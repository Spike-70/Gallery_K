"""이미지 검증·변환 파이프라인 (백엔드 문서 §10.1, PRD §8.2).

**요청 안에서 동기로 끝낸다.** 이벤트 워커를 두면 S3 이벤트 구독·별도 Lambda·처리 지연
폴링·정체 감지 배치가 함께 따라온다. 한 장 처리 시간은 요청 타임아웃 안에 충분히
들어가고, 여러 장은 클라이언트가 병렬 업로드하므로 요청도 병렬로 나뉜다.

처리 규격
  * 썸네일 400×400 정사각 크롭 WebP q80
  * 디스플레이 긴 변 1600px WebP q85
  * LQIP 16px 폭 WebP data URL
  * EXIF 방향 보정 · EXIF 개인정보 제거 · 색 프로파일 sRGB 변환

색 변환은 미술 작품에서 특히 중요하다 — Adobe RGB로 촬영된 원본을 그대로 내리면
브라우저가 sRGB로 간주해 색이 눕는다.

**실패는 재업로드로만 복구한다.** 자동 재시도를 하지 않는 이유는 대부분 파일 자체의
문제이고 재시도는 대기 시간만 늘리기 때문이다.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Final

from chalicelib.config.constants import (
    IMAGE_DISPLAY_LONG_EDGE,
    IMAGE_DISPLAY_QUALITY,
    IMAGE_LQIP_QUALITY,
    IMAGE_LQIP_WIDTH,
    IMAGE_MAX_PIXELS,
    IMAGE_THUMB_QUALITY,
    IMAGE_THUMB_SIZE,
    UPLOAD_ALLOWED_MIME,
    UPLOAD_MAX_BYTES,
)
from chalicelib.core.logging import get_logger, log_event
from chalicelib.db.models.enums import ImageErrorCode

logger = get_logger("image")

#: 매직 바이트 (2차 검증). 서명 정책이 1차, 이것이 2차다.
_MAGIC: Final[tuple[tuple[bytes, str], ...]] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)


class ImageProcessingError(Exception):
    """사유 코드를 들고 다니는 실패. 상태와 함께 기록되고 재업로드로만 복구된다."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Derivative:
    suffix: str
    data: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    width: int
    height: int
    origin_bytes: int
    origin_mime: str
    thumb: Derivative
    display: Derivative
    lqip: str


def sniff_mime(data: bytes) -> str | None:
    """확장자·헤더가 아니라 **실제 바이트**를 본다."""
    for signature, mime in _MAGIC:
        if data.startswith(signature):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def process(data: bytes, *, declared_mime: str) -> ProcessedImage:
    """원본 바이트를 검증하고 파생 3종을 만든다."""
    from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

    if len(data) > UPLOAD_MAX_BYTES:
        raise ImageProcessingError(ImageErrorCode.TOO_LARGE)

    actual_mime = sniff_mime(data)
    if actual_mime is None:
        raise ImageProcessingError(ImageErrorCode.NOT_AN_IMAGE)
    if actual_mime not in UPLOAD_ALLOWED_MIME or actual_mime != declared_mime:
        # 선언한 형식과 실제가 다르면 거절한다. 확장자만 바꾼 파일을 통과시키지 않는다.
        raise ImageProcessingError(ImageErrorCode.MIME_MISMATCH)

    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            if opened.width * opened.height > IMAGE_MAX_PIXELS:
                raise ImageProcessingError(ImageErrorCode.TOO_MANY_PIXELS)

            # EXIF 방향 보정. 세로로 찍은 사진이 눕지 않게 한다.
            image = ImageOps.exif_transpose(opened) or opened
            image = _to_srgb(image, ImageCms)
            # RGB로 정규화하면서 EXIF가 함께 떨어져 나간다 — 개인정보 제거를 겸한다.
            image = image.convert("RGB")

            width, height = image.size
            thumb = _thumbnail(image, ImageOps)
            display = _display(image)
            lqip = _lqip(image)
    except ImageProcessingError:
        raise
    except UnidentifiedImageError as exc:
        raise ImageProcessingError(ImageErrorCode.NOT_AN_IMAGE) from exc
    except Exception as exc:
        log_event(logger, "image.decode_failed", message=str(exc))
        raise ImageProcessingError(ImageErrorCode.DECODE_FAILED) from exc

    return ProcessedImage(
        width=width,
        height=height,
        origin_bytes=len(data),
        origin_mime=actual_mime,
        thumb=thumb,
        display=display,
        lqip=lqip,
    )


def _to_srgb(image: Any, cms: Any) -> Any:
    """색 프로파일을 sRGB로 맞춘다. 프로파일이 없으면 sRGB로 간주한다."""
    profile = image.info.get("icc_profile")
    if not profile:
        return image
    try:
        source = cms.ImageCmsProfile(io.BytesIO(profile))
        target = cms.createProfile("sRGB")
        return cms.profileToProfile(image, source, target, outputMode="RGB")
    except Exception:
        # 깨진 프로파일 때문에 업로드 전체를 실패시키지 않는다.
        log_event(logger, "image.icc_ignored")
        return image


def _thumbnail(image: Any, ops: Any) -> Derivative:
    """400×400 정사각 크롭. 그리드가 격자로 정렬되려면 비율이 하나여야 한다."""
    cropped = ops.fit(image, (IMAGE_THUMB_SIZE, IMAGE_THUMB_SIZE), method=_resampling())
    return Derivative("thumb.webp", _encode(cropped, IMAGE_THUMB_QUALITY), "image/webp")


def _display(image: Any) -> Derivative:
    """긴 변 1600px. 원본 비율을 유지한다 — C-2는 작품을 있는 비율로 보여준다."""
    resized = image.copy()
    resized.thumbnail((IMAGE_DISPLAY_LONG_EDGE, IMAGE_DISPLAY_LONG_EDGE), _resampling())
    return Derivative("display.webp", _encode(resized, IMAGE_DISPLAY_QUALITY), "image/webp")


def _lqip(image: Any) -> str:
    """16px 폭 블러 플레이스홀더. data URL이라 추가 왕복이 없다."""
    ratio = image.height / image.width if image.width else 1
    tiny = image.copy()
    tiny.thumbnail((IMAGE_LQIP_WIDTH, max(1, round(IMAGE_LQIP_WIDTH * ratio))), _resampling())
    encoded = base64.b64encode(_encode(tiny, IMAGE_LQIP_QUALITY)).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def _encode(image: Any, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=4)
    return buffer.getvalue()


def _resampling() -> Any:
    from PIL import Image

    return Image.Resampling.LANCZOS

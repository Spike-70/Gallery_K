"""이미지 변환 파이프라인 (백엔드 문서 §10.1, PRD §8.2)."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from chalicelib.config.constants import (
    IMAGE_DISPLAY_LONG_EDGE,
    IMAGE_THUMB_SIZE,
    UPLOAD_MAX_BYTES,
)
from chalicelib.db.models.enums import ImageErrorCode
from chalicelib.services import image_service


def _jpeg(width: int, height: int, *, exif: bytes | None = None) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), (120, 40, 200))
    if exif is not None:
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_three_derivatives_match_the_documented_specs() -> None:
    result = image_service.process(_jpeg(2400, 1600), declared_mime="image/jpeg")

    with Image.open(io.BytesIO(result.thumb.data)) as thumb:
        assert thumb.size == (IMAGE_THUMB_SIZE, IMAGE_THUMB_SIZE)  # 정사각 크롭
        assert thumb.format == "WEBP"

    with Image.open(io.BytesIO(result.display.data)) as display:
        assert max(display.size) == IMAGE_DISPLAY_LONG_EDGE  # 긴 변 1600
        assert display.size == (1600, 1067)  # 원본 비율 유지
        assert display.format == "WEBP"

    assert result.width == 2400
    assert result.height == 1600


def test_lqip_is_a_tiny_inline_data_url() -> None:
    result = image_service.process(_jpeg(2400, 1600), declared_mime="image/jpeg")
    assert result.lqip.startswith("data:image/webp;base64,")
    payload = base64.b64decode(result.lqip.split(",", 1)[1])
    with Image.open(io.BytesIO(payload)) as tiny:
        assert tiny.width == 16
    # 추가 왕복이 없어야 의미가 있으므로 크기가 작아야 한다.
    assert len(result.lqip) < 2000


def test_exif_orientation_is_corrected() -> None:
    """세로로 찍은 사진이 눕지 않아야 한다."""
    exif = Image.Exif()
    exif[274] = 6  # Orientation: 90도 회전 필요
    rotated = image_service.process(_jpeg(400, 200, exif=exif.tobytes()), declared_mime="image/jpeg")
    # 방향 보정이 적용되면 가로세로가 뒤바뀐다.
    assert (rotated.width, rotated.height) == (200, 400)


def test_exif_personal_data_is_removed() -> None:
    exif = Image.Exif()
    exif[271] = "SecretCamera"  # Make
    exif[305] = "PrivateSoftware"  # Software
    result = image_service.process(_jpeg(800, 600, exif=exif.tobytes()), declared_mime="image/jpeg")

    with Image.open(io.BytesIO(result.display.data)) as display:
        assert not display.getexif()
    assert b"SecretCamera" not in result.display.data
    assert b"PrivateSoftware" not in result.display.data


def test_magic_bytes_are_checked_not_the_declared_type() -> None:
    """서명 정책이 1차, 매직 바이트가 2차다."""
    with pytest.raises(image_service.ImageProcessingError) as caught:
        image_service.process(b"GIF89a\x00\x00 not really", declared_mime="image/jpeg")
    assert caught.value.code == ImageErrorCode.NOT_AN_IMAGE


def test_declared_type_must_match_the_actual_bytes() -> None:
    """확장자만 바꾼 파일을 통과시키지 않는다."""
    with pytest.raises(image_service.ImageProcessingError) as caught:
        image_service.process(_jpeg(400, 400), declared_mime="image/png")
    assert caught.value.code == ImageErrorCode.MIME_MISMATCH


def test_oversized_payload_is_refused() -> None:
    with pytest.raises(image_service.ImageProcessingError) as caught:
        image_service.process(b"\xff\xd8\xff" + b"0" * UPLOAD_MAX_BYTES, declared_mime="image/jpeg")
    assert caught.value.code == ImageErrorCode.TOO_LARGE


def test_sniff_recognises_the_three_allowed_formats() -> None:
    assert image_service.sniff_mime(_jpeg(10, 10)) == "image/jpeg"

    png = io.BytesIO()
    Image.new("RGB", (10, 10)).save(png, format="PNG")
    assert image_service.sniff_mime(png.getvalue()) == "image/png"

    webp = io.BytesIO()
    Image.new("RGB", (10, 10)).save(webp, format="WEBP")
    assert image_service.sniff_mime(webp.getvalue()) == "image/webp"

    assert image_service.sniff_mime(b"RIFF____NOTWEBP") is None


def test_png_transparency_is_flattened_to_rgb() -> None:
    """WebP 변환 전에 RGB로 정규화한다 — 색 프로파일 처리와 EXIF 제거를 겸한다."""
    buffer = io.BytesIO()
    Image.new("RGBA", (500, 500), (10, 20, 30, 128)).save(buffer, format="PNG")
    result = image_service.process(buffer.getvalue(), declared_mime="image/png")
    with Image.open(io.BytesIO(result.thumb.data)) as thumb:
        assert thumb.mode in {"RGB", "RGBX"}

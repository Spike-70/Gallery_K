"""미디어 접근 (백엔드 문서 §10, API 문서 §3.1·§6.10).

버킷은 비공개이며 **접근 수단은 presigned URL 하나뿐이다.** 서명 쿠키·키페어·전용 세션
갱신 API를 쓰지 않는다 — 클라이언트가 관리해야 할 미디어 자격 상태가 없어진다.

서명 방식이 바뀌더라도 호출부는 모른다. 이 모듈 밖에서 `integrations.storage`를 부르지
않는 것이 그 캡슐화의 전부다(교차검토 X-17).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import (
    MEDIA_ARTWORK_PREFIX,
    MEDIA_UPLOAD_PREFIX,
    UPLOAD_ALLOWED_MIME,
    UPLOAD_MAX_BYTES,
    UPLOAD_MIME_EXTENSIONS,
    UPLOAD_URL_TTL_SECONDS,
)
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import new_request_id
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.timeutil import format_rfc3339, now_utc
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, Exhibition
from chalicelib.db.models.enums import ImageErrorCode, ImageStatus
from chalicelib.integrations import storage
from chalicelib.services import setting_service
from chalicelib.services.setting_service import SettingKey
from chalicelib.utils.text import safe_extension

logger = get_logger("media")


def url_ttl_seconds(session: Session) -> int:
    return setting_service.get_int(session, SettingKey.MEDIA_URL_TTL_SECONDS)


def image_set(artwork: Artwork, *, ttl_seconds: int) -> dict[str, Any] | None:
    """`ImageSet` (API 문서 §3.1).

    `ready`가 아니면 `None`이다 — 프런트가 자리표시자를 그린다(API 문서 §9.12).
    """
    if artwork.image_status != ImageStatus.READY:
        return None
    if not (artwork.image_thumb_key and artwork.image_display_key):
        return None

    width, height = artwork.image_width, artwork.image_height
    return {
        "thumb_url": storage.presigned_get(artwork.image_thumb_key, expires_in=ttl_seconds),
        "display_url": storage.presigned_get(artwork.image_display_key, expires_in=ttl_seconds),
        # 원본은 전체 화면 확대 요청 시에만 쓰며 그 외에는 미리 로드하지 않는다.
        "origin_url": (
            storage.presigned_get(artwork.image_origin_key, expires_in=ttl_seconds)
            if artwork.image_origin_key
            else None
        ),
        "lqip": artwork.image_lqip,
        "width": width,
        "height": height,
        # 레이아웃 시프트 방지용. 소수점 4자리 (API 문서 §3.1).
        "aspect_ratio": round(width / height, 4) if width and height else None,
    }


# ── 오브젝트 키 ────────────────────────────────────────────────────────────
# 업로드 착지 경로와 확정 경로를 분리한다 — 처리에 실패한 업로드가 서비스 경로에
# 남지 않게 하기 위함이다(백엔드 문서 §10.2).


def pending_key(exhibition_date: _dt.date, artwork_id: uuid.UUID, extension: str) -> str:
    return f"{MEDIA_UPLOAD_PREFIX}/{exhibition_date.isoformat()}/{artwork_id}/{new_request_id()}{extension}"


def final_key(exhibition_date: _dt.date, artwork_id: uuid.UUID, name: str) -> str:
    return f"{MEDIA_ARTWORK_PREFIX}/{exhibition_date.isoformat()}/{artwork_id}/{name}"


def artwork_object_keys(artwork: Artwork) -> list[str]:
    """그림이 참조하는 오브젝트 전부. 정리 배치가 이 목록을 기준으로 살아 있는 키를 센다."""
    return [
        key
        for key in (
            artwork.image_origin_key,
            artwork.image_display_key,
            artwork.image_thumb_key,
            artwork.image_pending_key,
        )
        if key
    ]


# ── 업로드 자격 발급 ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UploadRequest:
    position: int
    filename: str
    content_type: str
    size_bytes: int


def issue_upload_credentials(
    session: Session,
    *,
    exhibition_date: _dt.date,
    files: list[UploadRequest],
    overwrite: bool,
) -> list[dict[str, Any]]:
    """슬롯 행을 확보하고 presigned POST를 발급한다 (API 문서 §9.8).

    사전 검증(크기·형식)은 UX용이고, 최종 강제는 **서명 정책**이 한다.

    대상 전시도 여기서 찾는다 — 라우트가 모델을 만지지 않게 하기 위함이다(문서 §4.3).
    """
    from chalicelib.services import artwork_admin_service, exhibition_admin_service, publishing

    exhibition_id = exhibition_admin_service.find_exhibition(session, exhibition_date).id

    seen: set[int] = set()
    for item in files:
        if item.position in seen:
            raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="같은 자리를 두 번 요청했습니다")
        seen.add(item.position)
        if item.size_bytes > UPLOAD_MAX_BYTES:
            raise AppError(ErrorCode.UPLOAD_FILE_TOO_LARGE, details={"max_bytes": UPLOAD_MAX_BYTES})
        if item.content_type not in UPLOAD_ALLOWED_MIME:
            raise AppError(ErrorCode.UPLOAD_MIME_NOT_ALLOWED, details={"allowed": list(UPLOAD_ALLOWED_MIME)})

    expires_at = now_utc() + _dt.timedelta(seconds=UPLOAD_URL_TTL_SECONDS)
    uploads: list[dict[str, Any]] = []

    for item in files:
        artwork = artwork_admin_service.get_or_create_slot(session, exhibition_id, item.position)
        if artwork.image_status == ImageStatus.READY and not overwrite:
            raise AppError(ErrorCode.ARTWORK_SLOT_OCCUPIED, details={"position": item.position})

        extension = UPLOAD_MIME_EXTENSIONS.get(item.content_type, safe_extension(item.filename, ".jpg"))
        key = pending_key(exhibition_date, artwork.id, extension)
        credential = storage.presigned_post(
            key,
            content_type=item.content_type,
            max_bytes=UPLOAD_MAX_BYTES,
            expires_in=UPLOAD_URL_TTL_SECONDS,
        )
        artwork_admin_service.mark_uploading(session, artwork.id, pending_key=key, overwrite=overwrite)
        uploads.append(
            {
                "position": item.position,
                "artwork_id": str(artwork.id),
                "upload_url": credential["url"],
                "method": "POST",
                "fields": credential["fields"],
                "object_key": key,
                "expires_at": format_rfc3339(expires_at),
            }
        )

    # 슬롯 행이 새로 생겼을 수 있다. 카운터는 **그림 변경과 같은 트랜잭션에서**
    # 재계산한다(DB 문서 §4.4) — 그러지 않으면 달력의 진행률이 실제와 어긋난다.
    publishing.recount(session, exhibition_id)
    return uploads


# ── 업로드 완료 통지 ───────────────────────────────────────────────────────


def complete_upload(
    session: Session, *, artwork_id: uuid.UUID, object_key: str, today: _dt.date
) -> dict[str, Any]:
    """**이 요청 안에서 동기로** 검증·변환하고 `ready`로 전환한다 (API 문서 §9.9).

    응답이 곧 처리 완료 통지이므로 클라이언트 폴링이 필요 없다. 중복 호출은 무해하다 —
    이미 `ready`이고 같은 원본이면 현재 상태만 돌려준다.
    """
    from chalicelib.services import artwork_admin_service, image_service, publishing

    artwork = artwork_admin_service.artwork_of(session, artwork_id)
    ttl = url_ttl_seconds(session)

    if artwork.image_status == ImageStatus.READY and artwork.image_pending_key != object_key:
        return _complete_response(artwork, ttl_seconds=ttl)

    if artwork.image_pending_key != object_key:
        # 발급한 적 없는 키로 완료를 통지했다. 만료된 자격이거나 잘못된 호출이다.
        raise AppError(ErrorCode.UPLOAD_EXPIRED)

    try:
        raw = storage.get_object(object_key)
    except Exception as exc:
        _mark_failed(session, artwork.id, ImageErrorCode.OBJECT_MISSING)
        log_event(logger, "image.origin_missing", message=str(exc))
        session.refresh(artwork)
        return _complete_response(artwork, ttl_seconds=ttl)

    declared = artwork.image_mime or image_service.sniff_mime(raw) or ""
    try:
        processed = image_service.process(raw, declared_mime=declared)
    except image_service.ImageProcessingError as error:
        _mark_failed(session, artwork.id, error.code)
        session.refresh(artwork)
        return _complete_response(artwork, ttl_seconds=ttl)

    exhibition_date = _exhibition_date_of(session, artwork.exhibition_id)
    origin_extension = UPLOAD_MIME_EXTENSIONS.get(processed.origin_mime, ".jpg")
    origin_key = final_key(exhibition_date, artwork.id, f"origin{origin_extension}")
    display_key = final_key(exhibition_date, artwork.id, processed.display.suffix)
    thumb_key = final_key(exhibition_date, artwork.id, processed.thumb.suffix)

    # S3 쓰기를 먼저 끝내고 DB 갱신은 **마지막에 한 번만** 한다.
    #
    # 문서 §4.4는 "외부 호출은 트랜잭션 안에서 하지 않는다"고 규정하지만, 이 경로는
    # 인증 단계에서 이미 요청 트랜잭션이 열려 있어 그것을 문자 그대로 지킬 수 없다.
    # 대신 규칙이 막으려는 것 — **행 잠금을 쥔 채로 네트워크를 기다리는 상황** — 은
    # 만들지 않는다. 쓰기는 S3 작업이 모두 끝난 뒤 한 문장으로 일어난다.
    storage.put_object(origin_key, data=raw, content_type=processed.origin_mime)
    storage.put_object(display_key, data=processed.display.data, content_type="image/webp")
    storage.put_object(thumb_key, data=processed.thumb.data, content_type="image/webp")

    now = now_utc()
    q.update(
        session,
        Artwork,
        where={"id": artwork.id},
        values={
            "image_status": ImageStatus.READY,
            "image_origin_key": origin_key,
            "image_display_key": display_key,
            "image_thumb_key": thumb_key,
            "image_lqip": processed.lqip,
            "image_width": processed.width,
            "image_height": processed.height,
            "image_bytes": processed.origin_bytes,
            "image_mime": processed.origin_mime,
            "image_error_code": None,
            "image_ready_at": now,
            "updated_at": now,
        },
        bump_version=False,
    )
    session.expire(artwork)
    session.refresh(artwork)

    # 마지막 한 점이 준비되면 그 순간 발행 조건이 충족될 수 있다.
    #
    # `today`는 **반드시 서버가 판정한 오늘**이어야 한다. 전시의 발행일을 넘기면
    # `apply`의 백필 판정(`exhibition_date < today`)이 항상 거짓이 되어, 과거 드래프트에
    # 마지막 이미지를 올리는 것만으로 지난 날짜가 발행되어 버린다(PRD §4.3).
    exhibition = q.fetch_one(session, Exhibition, where={"id": artwork.exhibition_id})
    if exhibition is not None:
        publishing.apply(session, exhibition, today=today)

    log_event(logger, "image.ready", artwork_id=str(artwork.id))
    return _complete_response(artwork, ttl_seconds=ttl)


def _mark_failed(session: Session, artwork_id: uuid.UUID, code: str) -> None:
    """실패는 상태와 사유 코드를 기록하고 **재업로드로만 복구**한다."""
    q.update(
        session,
        Artwork,
        where={"id": artwork_id},
        values={
            "image_status": ImageStatus.FAILED,
            "image_error_code": code,
            "updated_at": now_utc(),
        },
        bump_version=False,
    )
    log_event(logger, "image.failed", artwork_id=str(artwork_id), reason=code)


def _complete_response(artwork: Artwork, *, ttl_seconds: int) -> dict[str, Any]:
    return {
        "artwork_id": str(artwork.id),
        "image_status": artwork.image_status,
        "images": image_set(artwork, ttl_seconds=ttl_seconds),
        "image_error_code": artwork.image_error_code,
    }


def _exhibition_date_of(session: Session, exhibition_id: uuid.UUID) -> _dt.date:
    exhibition = q.fetch_one(session, Exhibition, where={"id": exhibition_id}, columns=["exhibition_date"])
    if exhibition is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND)
    date_value: _dt.date = exhibition["exhibition_date"]
    return date_value

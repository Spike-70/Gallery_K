"""그림 슬롯 관리 (API 문서 §9.5–§9.7, PRD §6.10).

슬롯은 **항상 12개**다. 비어 있어도 자리 표시자를 반환한다 — 그 계약이 B-2 화면의
3×4 버튼 그리드를 단순하게 만든다.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import ARTWORK_COUNT
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import Artwork
from chalicelib.db.models.enums import ImageStatus
from chalicelib.services import media_service
from chalicelib.utils.text import normalize_text

#: 큐레이터가 직접 채우는 본문 필드. 이미지 관련 필드는 업로드 경로만 건드린다.
EDITABLE_FIELDS = ("title", "artist", "year_text", "description", "collection", "source_url")


def empty_slot(position: int) -> dict[str, Any]:
    return {
        "position": position,
        "artwork_id": None,
        "title": None,
        "artist": None,
        "year_text": None,
        "description": None,
        "collection": None,
        "source_url": None,
        "image_status": ImageStatus.EMPTY,
        "image": None,
        "image_error_code": None,
        "is_complete": False,
        "version": None,
    }


def serialize_slot(artwork: Artwork, *, ttl_seconds: int) -> dict[str, Any]:
    """`AdminArtworkSlot` (API 문서 §9.3)."""
    return {
        "position": artwork.position,
        "artwork_id": str(artwork.id),
        "title": artwork.title,
        "artist": artwork.artist,
        "year_text": artwork.year_text,
        "description": artwork.description,
        "collection": artwork.collection,
        "source_url": artwork.source_url,
        "image_status": artwork.image_status,
        "image": media_service.image_set(artwork, ttl_seconds=ttl_seconds),
        "image_error_code": artwork.image_error_code,
        "is_complete": artwork.is_complete,
        "version": artwork.version,
    }


def slots_of(session: Session, exhibition_id: uuid.UUID, *, ttl_seconds: int) -> list[dict[str, Any]]:
    """항상 12개. 채워진 자리만 실제 행으로 대체한다."""
    rows = q.fetch(session, Artwork, where={"exhibition_id": exhibition_id}, order_by=["position"])
    by_position = {row.position: row for row in rows}
    return [
        serialize_slot(by_position[position], ttl_seconds=ttl_seconds)
        if position in by_position
        else empty_slot(position)
        for position in range(1, ARTWORK_COUNT + 1)
    ]


def get_or_create_slot(session: Session, exhibition_id: uuid.UUID, position: int) -> Artwork:
    existing = q.fetch_one(session, Artwork, where={"exhibition_id": exhibition_id, "position": position})
    if existing is not None:
        return existing
    return q.insert(session, Artwork, {"exhibition_id": exhibition_id, "position": position})


def save_slot(
    session: Session,
    exhibition_id: uuid.UUID,
    position: int,
    *,
    values: dict[str, Any],
    expected_version: int | None,
) -> Artwork:
    """PUT 의미론 — 보낸 전체 상태로 덮어쓴다.

    빈 문자열은 NULL로 접는다. "값 없음"의 표현이 둘이면 완성 판정(생성 컬럼)이 흔들린다.
    """
    artwork = get_or_create_slot(session, exhibition_id, position)
    payload: dict[str, Any] = {field: normalize_text(values.get(field)) for field in EDITABLE_FIELDS}
    payload["updated_at"] = now_utc()

    q.update(
        session,
        Artwork,
        where={"id": artwork.id},
        values=payload,
        expected_version=expected_version,
    )
    session.expire(artwork)
    session.refresh(artwork)
    return artwork


def clear_slot(session: Session, exhibition_id: uuid.UUID, position: int) -> None:
    """슬롯 비우기.

    S3 오브젝트는 즉시 지우지 않고 7일 뒤 정리 배치가 회수한다(DB 문서 §8.3) — 삭제를
    되돌리고 싶은 순간이 실제로 있고, 그때 원본이 남아 있는 편이 낫다.
    """
    q.delete(session, Artwork, where={"exhibition_id": exhibition_id, "position": position})


def reorder(session: Session, exhibition_id: uuid.UUID, order: list[dict[str, Any]]) -> None:
    """전체 슬롯의 **최종 상태 선언**이므로 재시도가 안전하다 (API 문서 §9.7).

    슬롯 유니크가 `DEFERRABLE`이므로 한 트랜잭션 안에서 일괄 재할당하면 된다.
    임시 오프셋 트릭을 쓰지 않는다(DB 문서 §4.5).
    """
    positions = [item["position"] for item in order]
    if len(set(positions)) != len(positions):
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="자리 번호가 중복되었습니다")
    if any(not 1 <= position <= ARTWORK_COUNT for position in positions):
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="자리 번호가 범위를 벗어났습니다")

    owned = {
        row["id"]: row["position"]
        for row in q.fetch(
            session, Artwork, where={"exhibition_id": exhibition_id}, columns=["id", "position"]
        )
    }
    requested = {uuid.UUID(str(item["artwork_id"])) for item in order}
    if not requested <= set(owned):
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)

    session.execute(_defer_constraints())
    now = now_utc()
    q.bulk_update(
        session,
        Artwork,
        [
            {"id": uuid.UUID(str(item["artwork_id"])), "position": item["position"], "updated_at": now}
            for item in order
        ],
    )


def _defer_constraints() -> Any:
    from sqlalchemy import text

    return text("SET CONSTRAINTS uq_artwork_exhibition_position DEFERRED")


def mark_uploading(session: Session, artwork_id: uuid.UUID, *, pending_key: str, overwrite: bool) -> None:
    q.update(
        session,
        Artwork,
        where={"id": artwork_id},
        values={
            "image_status": ImageStatus.UPLOADING,
            "image_pending_key": pending_key,
            "image_error_code": None,
            "image_uploaded_at": now_utc(),
        },
        bump_version=False,
    )


def artwork_of(session: Session, artwork_id: uuid.UUID) -> Artwork:
    artwork = q.fetch_one(session, Artwork, where={"id": artwork_id})
    if artwork is None:
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)
    return artwork


def slot_of(session: Session, exhibition_id: uuid.UUID, position: int, *, ttl_seconds: int) -> dict[str, Any]:
    artwork = q.fetch_one(session, Artwork, where={"exhibition_id": exhibition_id, "position": position})
    return serialize_slot(artwork, ttl_seconds=ttl_seconds) if artwork else empty_slot(position)

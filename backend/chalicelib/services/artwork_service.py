"""그림 — 관람자 관점 (API 문서 §3.2·§3.3·§7.5).

그리드에는 **작가명만** 노출한다. 제목까지 넣으면 그리드가 텍스트로 가득 차 그림이
죽는다(PRD §6.5). 제목은 대체 텍스트 구성용으로만 내려간다.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import ARTWORK_COUNT
from chalicelib.db import query as q
from chalicelib.db.models import Artwork, ArtworkViewLog
from chalicelib.services import media_service


def viewed_artwork_ids(
    session: Session, *, user_id: uuid.UUID | None, exhibition_id: uuid.UUID
) -> set[uuid.UUID]:
    """ "열어봄" 표식은 **전시 기준**으로 조회한다 (DB 문서 §4.7).

    연장된 같은 전시를 이틀에 걸쳐 봐도 어제 본 8점은 오늘도 표식을 단다.
    그리드 전체를 한 번의 질의로 채우므로 N+1이 생기지 않는다.
    """
    if user_id is None:
        return set()
    rows = q.fetch(
        session,
        ArtworkViewLog,
        where={"user_id": user_id, "exhibition_id": exhibition_id},
        columns=["artwork_id"],
    )
    return {row["artwork_id"] for row in rows}


def serialize_summary(artwork: Artwork, *, is_viewed: bool, ttl_seconds: int) -> dict[str, Any]:
    """`ArtworkSummary` (API 문서 §3.2)."""
    return {
        "id": str(artwork.id),
        "position": artwork.position,
        "artist": artwork.artist or "",
        "title": artwork.title or "",
        "image": media_service.image_set(artwork, ttl_seconds=ttl_seconds),
        "is_viewed": is_viewed,
    }


def serialize_detail(
    artwork: Artwork,
    *,
    is_viewed: bool,
    ttl_seconds: int,
    prev_artwork_id: uuid.UUID | None,
    next_artwork_id: uuid.UUID | None,
) -> dict[str, Any]:
    """`ArtworkDetail` (API 문서 §3.3)."""
    return {
        **serialize_summary(artwork, is_viewed=is_viewed, ttl_seconds=ttl_seconds),
        "year_text": artwork.year_text or "",
        "description": artwork.description or "",
        "collection": artwork.collection,
        "source_url": artwork.source_url,
        "prev_artwork_id": str(prev_artwork_id) if prev_artwork_id else None,
        "next_artwork_id": str(next_artwork_id) if next_artwork_id else None,
    }


def artists_of(artworks: list[Artwork]) -> list[str]:
    """중복 제거된 작가 목록. C-1 하단에 오늘의 폭을 가늠하게 한다 (PRD §6.6).

    순서를 유지한다 — 정렬하면 전시의 흐름과 무관한 가나다순이 된다.
    """
    seen: dict[str, None] = {}
    for artwork in artworks:
        if artwork.artist:
            seen.setdefault(artwork.artist, None)
    return list(seen)


def position_label(position: int, total: int = ARTWORK_COUNT) -> str:
    """`3 / 12` — 서버가 완성한 문자열 (API 문서 §7.5)."""
    return f"{position} / {total}"


def neighbours(artworks: list[Artwork], current: Artwork) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """스와이프 대상. 첫 점이면 이전이 없고 마지막 점이면 다음이 없다."""
    ordered = sorted(artworks, key=lambda item: item.position)
    index = next((i for i, item in enumerate(ordered) if item.id == current.id), None)
    if index is None:
        return None, None
    previous = ordered[index - 1].id if index > 0 else None
    following = ordered[index + 1].id if index + 1 < len(ordered) else None
    return previous, following


def load_for_exhibition(session: Session, exhibition_id: uuid.UUID) -> list[Artwork]:
    return q.fetch(
        session,
        Artwork,
        where={"exhibition_id": exhibition_id},
        order_by=["position"],
    )


# ── 라우트가 소비하는 완성된 응답 ──────────────────────────────────────────


def detail_response(
    session: Session, *, artwork_id: uuid.UUID, today: Any, user_id: Any
) -> dict[str, Any] | None:
    """C-2 화면 (API 문서 §7.5). 보이지 않는 그림이면 `None`."""
    from chalicelib.services import exhibition_service
    from chalicelib.services.artwork_lookup import find_visible_artwork

    found = find_visible_artwork(session, artwork_id, today=today)
    if found is None:
        return None
    artwork, exhibition = found

    siblings = load_for_exhibition(session, exhibition.id)
    previous, following = neighbours(siblings, artwork)
    viewed = viewed_artwork_ids(session, user_id=user_id, exhibition_id=exhibition.id)
    is_carried_over, label = exhibition_service.carryover_state(exhibition.exhibition_date, today)

    return {
        "artwork": serialize_detail(
            artwork,
            is_viewed=artwork.id in viewed,
            ttl_seconds=media_service.url_ttl_seconds(session),
            prev_artwork_id=previous,
            next_artwork_id=following,
        ),
        "exhibition": {
            "exhibition_date": exhibition.exhibition_date.isoformat(),
            "title": exhibition.title or "",
            "is_carried_over": is_carried_over,
            "carried_over_label": label,
        },
        "position_label": position_label(artwork.position, len(siblings)),
    }


def record_view(session: Session, *, artwork_id: uuid.UUID, user_id: uuid.UUID, today: Any) -> int | None:
    """C-2 진입 기록 (API 문서 §7.6). 보이지 않는 그림이면 `None`."""
    from chalicelib.services import view_log_service
    from chalicelib.services.artwork_lookup import find_visible_artwork

    found = find_visible_artwork(session, artwork_id, today=today)
    if found is None:
        return None
    artwork, exhibition = found
    return view_log_service.record_artwork_view(
        session,
        user_id=user_id,
        artwork_id=artwork.id,
        exhibition_id=exhibition.id,
        viewed_on=today,
    )

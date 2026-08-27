"""전시 — 관람자 관점 (PRD §4.3, API 문서 §7).

이 제품의 시간 축은 두 개다.
  * **발행일**(`exhibition_date`) — 큐레이터가 그 전시를 건 날짜. 전시에 영구히 귀속된다
  * **관람일**(`viewing_date`) — 관람자가 보고 있는 오늘

**규칙 1** — 관람자는 언제나 '가장 최근에 발행된 전시'를 본다. 관람자 화면에 빈 날은
존재하지 않으며, 별도의 연장 처리도 관리자의 조작도 필요 없다. 아래 질의 하나가
스킵과 연장을 모두 표현한다.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.timeutil import carried_over_label, format_date
from chalicelib.db import query as q
from chalicelib.db.models import Exhibition

#: 관람자에게 보이는 전시의 조건. 부분 인덱스 `ix_exhibition_visible`가 이것을 탄다.
VISIBLE = {"is_published": True, "is_hidden": False}


def find_current(session: Session, today: _dt.date, *, selectin: tuple[str, ...] = ()) -> Exhibition | None:
    """규칙 1의 구현. 오늘 발행분이 없으면 직전 발행 전시가 그대로 걸린다."""
    return q.fetch_one(
        session,
        Exhibition,
        where={**VISIBLE, "exhibition_date__lte": today},
        order_by=["-exhibition_date"],
        selectin=list(selectin),
    )


def find_by_date(
    session: Session, exhibition_date: _dt.date, *, selectin: tuple[str, ...] = ()
) -> Exhibition | None:
    """특정 발행일의 전시. 미발행·숨김·미래 날짜는 모두 부재로 응답한다(API 문서 §7.2)."""
    return q.fetch_one(
        session,
        Exhibition,
        where={**VISIBLE, "exhibition_date": exhibition_date},
        selectin=list(selectin),
    )


def carryover_state(exhibition_date: _dt.date, viewing_date: _dt.date) -> tuple[bool, str | None]:
    """연장 여부와 표시 문구.

    **서버가 계산해서 준다.** 클라이언트가 날짜를 비교해 문구를 만들면 단말 시계 오차가
    UI에 새어 나온다(PRD §6.1).
    """
    is_carried_over = exhibition_date < viewing_date
    return is_carried_over, carried_over_label(exhibition_date) if is_carried_over else None


def carried_over_days(session: Session, today: _dt.date) -> int:
    """오늘 기준 연속 연장 일수. 0이면 오늘 발행됐다는 뜻이다 (API 문서 §9.1)."""
    current = find_current(session, today)
    if current is None:
        return 0
    return (today - current.exhibition_date).days


def etag_of(exhibition: Exhibition) -> str:
    """`ETag`는 전시의 `updated_at` + `version`으로 만든다 (API 문서 §2.9)."""
    stamp = int(exhibition.updated_at.timestamp())
    return f'"{stamp}-{exhibition.version}"'


def serialize_detail(
    session: Session,
    exhibition: Exhibition,
    *,
    viewing_date: _dt.date,
    user_id: Any,
    is_archive_view: bool,
    ttl_seconds: int,
) -> dict[str, Any]:
    """`ExhibitionDetail` (API 문서 §3.5).

    `is_carried_over`와 `carried_over_label`을 **서버가 계산해서 준다.**
    """
    from chalicelib.services import artwork_service

    artworks = artwork_service.load_for_exhibition(session, exhibition.id)
    viewed = artwork_service.viewed_artwork_ids(session, user_id=user_id, exhibition_id=exhibition.id)
    is_carried_over, label = carryover_state(exhibition.exhibition_date, viewing_date)

    return {
        "exhibition_date": format_date(exhibition.exhibition_date),
        "title": exhibition.title or "",
        "theme": exhibition.theme or "",
        "artists": artwork_service.artists_of(artworks),
        "artworks": [
            artwork_service.serialize_summary(
                artwork, is_viewed=artwork.id in viewed, ttl_seconds=ttl_seconds
            )
            for artwork in artworks
        ],
        "viewing_date": format_date(viewing_date),
        "is_carried_over": is_carried_over,
        "carried_over_label": label,
        "is_archive_view": is_archive_view,
    }


def serialize_summary_row(
    exhibition: Exhibition,
    *,
    cover: Any,
    viewed_artwork_count: int,
) -> dict[str, Any]:
    """`ExhibitionSummary` (API 문서 §3.4)."""
    return {
        "exhibition_date": format_date(exhibition.exhibition_date),
        "title": exhibition.title or "",
        "cover_image": cover,
        "artwork_count": exhibition.artwork_count,
        "viewed_artwork_count": viewed_artwork_count,
        "is_viewed": viewed_artwork_count > 0,
    }


def list_archive(
    session: Session,
    *,
    user_id: Any,
    limit: int,
    cursor_key: str | None,
    cursor_id: str | None,
    archive_size: int,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], bool, tuple[str, str] | None]:
    """아카이브 목록 (API 문서 §7.3).

    목록의 단위는 날짜가 아니라 **전시**다. 발행이 뜸한 시기에도 목록이 비지 않도록
    "지난 30일"이 아니라 "최근 30개"로 센다(PRD §6.8). 연장된 날은 별도 행으로 나타나지
    않는다 — 그 전시는 이미 자기 발행일에 한 번 있기 때문이다.

    상한은 `app_setting.archive_size`이며 그 이상은 `has_more=false`로 끝난다.
    """
    from chalicelib.services import view_log_service

    # 상한이 30 남짓이므로 전체를 한 번에 가져와 커서를 그 안에서 적용한다.
    # 이렇게 하면 "전체 목록 상한"이 페이지를 넘어가도 정확히 지켜진다.
    window = q.fetch(
        session,
        Exhibition,
        where=VISIBLE,
        order_by=["-exhibition_date"],
        limit=archive_size,
    )

    if cursor_key is not None:
        remaining = [
            row
            for row in window
            if (row.exhibition_date.isoformat(), str(row.id)) < (cursor_key, cursor_id or "")
        ]
    else:
        remaining = window

    page = remaining[:limit]
    has_more = len(remaining) > limit
    next_cursor = (page[-1].exhibition_date.isoformat(), str(page[-1].id)) if page and has_more else None

    counts = (
        view_log_service.viewed_counts_by_exhibition(
            session, user_id=user_id, exhibition_ids=[row.id for row in page]
        )
        if user_id
        else {}
    )
    covers = _cover_images(session, [row.id for row in page], ttl_seconds=ttl_seconds)

    return (
        [
            serialize_summary_row(row, cover=covers.get(row.id), viewed_artwork_count=counts.get(row.id, 0))
            for row in page
        ],
        has_more,
        next_cursor,
    )


def _cover_images(session: Session, exhibition_ids: list[Any], *, ttl_seconds: int) -> dict[Any, Any]:
    """1번 슬롯 그림의 이미지 (API 문서 §3.4). 목록 전체를 한 번의 질의로 채운다."""
    if not exhibition_ids:
        return {}
    from chalicelib.db.models import Artwork
    from chalicelib.services import media_service

    rows = q.fetch(
        session,
        Artwork,
        where={"exhibition_id__in": exhibition_ids, "position": 1},
    )
    return {row.exhibition_id: media_service.image_set(row, ttl_seconds=ttl_seconds) for row in rows}


# ── 라우트가 소비하는 완성된 응답 ──────────────────────────────────────────
# 모델 객체는 서비스 밖으로 나가지 않는다(백엔드 문서 §4.3). 아래 함수들이 경계다.


def current_detail(session: Session, *, today: _dt.date, user_id: Any) -> tuple[dict[str, Any], str] | None:
    """C 화면. 없으면 `None` — 개관 전이라는 뜻이다."""
    from chalicelib.services import media_service

    exhibition = find_current(session, today)
    if exhibition is None:
        return None
    data = serialize_detail(
        session,
        exhibition,
        viewing_date=today,
        user_id=user_id,
        is_archive_view=False,
        ttl_seconds=media_service.url_ttl_seconds(session),
    )
    return data, etag_of(exhibition)


def detail_by_date(
    session: Session, *, exhibition_date: _dt.date, today: _dt.date, user_id: Any
) -> tuple[dict[str, Any], str] | None:
    """특정 발행일. 미발행·숨김·미래 날짜는 모두 `None`이다."""
    from chalicelib.services import media_service

    exhibition = find_by_date(session, exhibition_date)
    if exhibition is None or exhibition.exhibition_date > today:
        return None
    data = serialize_detail(
        session,
        exhibition,
        viewing_date=today,
        user_id=user_id,
        is_archive_view=True,
        ttl_seconds=media_service.url_ttl_seconds(session),
    )
    return data, etag_of(exhibition)


def visible_exhibition_id(session: Session, exhibition_date: _dt.date) -> Any | None:
    """입장 기록이 대상 전시를 확인할 때 쓴다."""
    exhibition = find_by_date(session, exhibition_date)
    return exhibition.id if exhibition else None


def preview_detail(session: Session, *, exhibition_date: _dt.date) -> dict[str, Any] | None:
    """미리보기 (API 문서 §9.12).

    관람자 컴포넌트를 그대로 재사용하기 위해 `ExhibitionDetail`과 **같은 스키마**를 준다.
    단 미발행 상태여도 반환하며 `is_carried_over=false`, `viewing_date`는 해당 날짜다.
    이미지가 아직 `ready`가 아닌 슬롯은 `image`가 `null`이고 프런트가 자리표시자를 그린다.
    """
    from chalicelib.services import media_service

    exhibition = q.fetch_one(session, Exhibition, where={"exhibition_date": exhibition_date})
    if exhibition is None:
        return None
    return serialize_detail(
        session,
        exhibition,
        viewing_date=exhibition_date,
        user_id=None,
        is_archive_view=False,
        ttl_seconds=media_service.url_ttl_seconds(session),
    )

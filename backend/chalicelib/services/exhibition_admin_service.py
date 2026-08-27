"""전시 편집 — 큐레이터 관점 (API 문서 §9.1–§9.4·§9.10–§9.12, PRD §6.9·§6.10).

**`edit_mode`를 서버가 결정한다.** 백필 금지·이어쓰기 조건은 도메인 규칙이며 프런트가
날짜 비교로 재구현하면 규칙이 두 곳에 존재하게 된다(API 문서 §3.9).

과거의 미발행일을 실패가 아니라 **연장**으로 표시하는 것은 의도적이다 — 스킵은 정상
동작이지 사고가 아니다(PRD §6.9).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import date_range, format_date, format_rfc3339, now_utc, week_start
from chalicelib.db import query as q
from chalicelib.db.models import Exhibition
from chalicelib.db.models.enums import EditMode, ExhibitionDayStatus
from chalicelib.db.queries.admin_calendar import fetch_calendar_rows
from chalicelib.services import artwork_admin_service, media_service, publishing
from chalicelib.utils.text import normalize_text


def _has_draft_content(row: dict[str, Any]) -> bool:
    """ "작업물 있음"의 정의 — 제목·테마 중 하나라도 비어 있지 않거나 그림이 1점 이상."""
    return bool(
        normalize_text(row.get("own_title"))
        or normalize_text(row.get("own_theme"))
        or (row.get("own_artwork_count") or 0) > 0
    )


def edit_mode_for(day: _dt.date, today: _dt.date, row: dict[str, Any]) -> str:
    """네 가지 모드 (API 문서 §3.9).

    * `edit`        — 이미 발행된 전시. 과거·오늘·미래 모두 수정할 수 있다
    * `create`      — 오늘·미래의 빈 날 또는 작업 중인 드래프트
    * `carry_draft` — 과거의 미발행일에 쓰다 만 작업물이 남아 있다
    * `locked`      — 과거의 빈 날. 백필 금지이므로 새로 쓸 수 없다
    """
    if row.get("own_is_published"):
        return EditMode.EDIT
    if day >= today:
        return EditMode.CREATE
    return EditMode.CARRY_DRAFT if _has_draft_content(row) else EditMode.LOCKED


def _day_status(day: _dt.date, row: dict[str, Any], today: _dt.date) -> str:
    """`Y` / `↑` / `N` (PRD §6.9).

    **`↑`(연장)은 과거에만, `N`(준비 안 됨)은 오늘·미래에만** 나타난다. 오늘 아직 걸지
    않은 상태를 연장으로 표시하면 "오늘 할 일"이 화면에서 사라진다. 반대로 과거의
    미발행일을 `N`으로 표시하면 지난 날짜마다 붉은 경고가 남아 죄책감을 준다 —
    스킵은 정상 동작이지 사고가 아니다.
    """
    if row.get("own_is_published") and not row.get("own_is_hidden"):
        return ExhibitionDayStatus.PUBLISHED
    hung_date = row.get("hung_date")
    if day < today and hung_date is not None and hung_date < day:
        return ExhibitionDayStatus.CARRIED_OVER
    return ExhibitionDayStatus.EMPTY


def serialize_day(row: dict[str, Any], *, today: _dt.date) -> dict[str, Any]:
    """`AdminExhibitionDay` (API 문서 §3.9)."""
    day: _dt.date = row["day"]
    status = _day_status(day, row, today)
    mode = edit_mode_for(day, today, row)
    carried = status == ExhibitionDayStatus.CARRIED_OVER

    return {
        "date": format_date(day),
        "status": status,
        "title": row.get("own_title"),
        "carried_from_date": format_date(row["hung_date"]) if carried else None,
        "carried_from_title": row.get("hung_title") if carried else None,
        "has_draft": bool(row.get("own_id")) and not row.get("own_is_published") and _has_draft_content(row),
        "draft_progress": {
            "artwork_count": row.get("own_artwork_count") or 0,
            "complete_artwork_count": row.get("own_complete_artwork_count") or 0,
            "has_title": bool(normalize_text(row.get("own_title"))),
            "has_theme": bool(normalize_text(row.get("own_theme"))),
        },
        "is_hidden": bool(row.get("own_is_hidden")),
        "is_editable": mode != EditMode.LOCKED,
        "edit_mode": mode,
        "is_today": day == today,
        "updated_at": format_rfc3339(row.get("own_updated_at")),
    }


def calendar(
    session: Session, *, from_date: _dt.date, to_date: _dt.date, today: _dt.date
) -> list[dict[str, Any]]:
    """요청 범위의 **모든 날짜를 빠짐없이** 포함한다 — 클라이언트가 날짜 시리즈를 만들지 않는다."""
    rows = fetch_calendar_rows(session, from_date=from_date, to_date=to_date)
    return [serialize_day(row, today=today) for row in rows]


# ── 편집 상태 조회·저장 ────────────────────────────────────────────────────


def _find(session: Session, exhibition_date: _dt.date) -> Exhibition | None:
    return q.fetch_one(session, Exhibition, where={"exhibition_date": exhibition_date})


def _carry_draft_source(
    session: Session, exhibition_date: _dt.date, today: _dt.date
) -> dict[str, Any] | None:
    """오늘 편집 화면을 열었을 때, 옮겨올 만한 과거 드래프트가 있으면 알려 준다."""
    if exhibition_date != today:
        return None
    candidate = q.fetch_one(
        session,
        Exhibition,
        where={"is_published": False, "exhibition_date__lt": today},
        order_by=["-exhibition_date"],
    )
    if candidate is None:
        return None
    if not (
        normalize_text(candidate.title) or normalize_text(candidate.theme) or candidate.artwork_count > 0
    ):
        return None
    return {
        "from_date": format_date(candidate.exhibition_date),
        "artwork_count": candidate.artwork_count,
    }


def admin_detail(session: Session, *, exhibition_date: _dt.date, today: _dt.date) -> dict[str, Any]:
    """`AdminExhibitionDetail` (API 문서 §9.3).

    **부재 오류가 발생하지 않는다.** 행이 없으면 빈 12슬롯과 `edit_mode`를 계산해 반환한다.
    """
    exhibition = _find(session, exhibition_date)
    ttl = media_service.url_ttl_seconds(session)

    if exhibition is None:
        row: dict[str, Any] = {"day": exhibition_date}
        return {
            "exhibition_date": format_date(exhibition_date),
            "title": None,
            "theme": None,
            "is_published": False,
            "published_at": None,
            "is_hidden": False,
            "edit_mode": edit_mode_for(exhibition_date, today, row),
            "can_publish": False,
            "publish_blockers": [publishing.MISSING_TITLE, publishing.MISSING_THEME],
            "slots": [artwork_admin_service.empty_slot(p) for p in range(1, 13)],
            "version": 0,
            "draft_updated_at": None,
            "carry_draft_source": _carry_draft_source(session, exhibition_date, today),
        }

    blockers = publishing.blockers_for(exhibition)
    blockers.extend(publishing.slot_blockers(session, exhibition.id))
    row = {
        "own_is_published": exhibition.is_published,
        "own_title": exhibition.title,
        "own_theme": exhibition.theme,
        "own_artwork_count": exhibition.artwork_count,
    }
    return {
        "exhibition_date": format_date(exhibition.exhibition_date),
        "title": exhibition.title,
        "theme": exhibition.theme,
        "is_published": exhibition.is_published,
        "published_at": format_rfc3339(exhibition.published_at),
        "is_hidden": exhibition.is_hidden,
        "edit_mode": edit_mode_for(exhibition_date, today, row),
        "can_publish": not blockers,
        "publish_blockers": blockers,
        "slots": artwork_admin_service.slots_of(session, exhibition.id, ttl_seconds=ttl),
        "version": exhibition.version,
        "draft_updated_at": format_rfc3339(exhibition.draft_updated_at),
        "carry_draft_source": _carry_draft_source(session, exhibition_date, today),
    }


def _guard_backfill(exhibition: Exhibition | None, exhibition_date: _dt.date, today: _dt.date) -> None:
    """과거 날짜에 **새 전시를 세우는 것**만 막는다.

    이미 발행된 과거 전시의 수정은 계속 허용한다(PRD §4.3). 막는 것은 '과거 날짜에 새
    전시가 생기는 것'이지 '어제 쓴 글을 오늘 쓰는 것'이 아니다.
    """
    if exhibition_date >= today:
        return
    if exhibition is not None and exhibition.is_published:
        return
    if exhibition is not None:
        # 과거 드래프트를 이어 쓰는 길은 `carry-draft`뿐이다.
        raise AppError(
            ErrorCode.EXHIBITION_BACKFILL_FORBIDDEN,
            details={"date": exhibition_date.isoformat(), "today": today.isoformat()},
        )
    raise AppError(
        ErrorCode.EXHIBITION_BACKFILL_FORBIDDEN,
        details={"date": exhibition_date.isoformat(), "today": today.isoformat()},
    )


def save_title_theme(
    session: Session,
    *,
    exhibition_date: _dt.date,
    title: str | None,
    theme: str | None,
    version: int | None,
    today: _dt.date,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """드래프트 자동 임시저장의 대상. 행이 없으면 생성한다 (API 문서 §9.4)."""
    exhibition = _find(session, exhibition_date)
    _guard_backfill(exhibition, exhibition_date, today)

    now = now_utc()
    if exhibition is None:
        exhibition = q.insert(
            session,
            Exhibition,
            {
                "exhibition_date": exhibition_date,
                "title": normalize_text(title),
                "theme": normalize_text(theme),
                "draft_updated_at": now,
                "created_by": actor_id,
            },
        )
    else:
        q.update(
            session,
            Exhibition,
            where={"id": exhibition.id},
            values={
                "title": normalize_text(title),
                "theme": normalize_text(theme),
                "draft_updated_at": now,
                "updated_at": now,
            },
            expected_version=version,
        )
        session.expire(exhibition)
        session.refresh(exhibition)

    state = publishing.apply(session, exhibition, today=today, actor_id=actor_id)
    session.refresh(exhibition)
    return {
        "exhibition_date": format_date(exhibition.exhibition_date),
        "version": exhibition.version,
        "draft_updated_at": format_rfc3339(exhibition.draft_updated_at),
        "is_published": state.is_published,
        "published_at": format_rfc3339(exhibition.published_at),
        "can_publish": state.can_publish,
        "publish_blockers": state.blockers,
        "published_now": state.published_now,
    }


def find_exhibition(session: Session, exhibition_date: _dt.date) -> Exhibition:
    """편집 대상 전시. 없으면 부재로 끝낸다.

    라우트가 `_find`를 직접 부르지 않도록 공개 진입점을 둔다.
    """
    exhibition = _find(session, exhibition_date)
    if exhibition is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": exhibition_date.isoformat()})
    return exhibition


def save_artwork_slot(
    session: Session,
    *,
    exhibition_date: _dt.date,
    position: int,
    values: dict[str, Any],
    expected_version: int | None,
    today: _dt.date,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """그림 한 자리를 저장하고 **전시 상태를 함께** 돌려준다 (API 문서 §9.5).

    그림 저장이 전시의 발행 조건을 바꿀 수 있으므로, 프런트가 저장 후 전시를 다시
    조회하지 않게 한 응답으로 끝낸다.
    """
    exhibition = find_exhibition(session, exhibition_date)
    artwork_admin_service.save_slot(
        session,
        exhibition.id,
        position,
        values=values,
        expected_version=expected_version,
    )
    return _slot_result(session, exhibition, position, today=today, actor_id=actor_id)


def clear_artwork_slot(
    session: Session,
    *,
    exhibition_date: _dt.date,
    position: int,
    today: _dt.date,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """슬롯 비우기 (API 문서 §9.6). 발행된 전시에서 비워도 발행 상태는 유지된다."""
    exhibition = find_exhibition(session, exhibition_date)
    artwork_admin_service.clear_slot(session, exhibition.id, position)
    return _slot_result(session, exhibition, position, today=today, actor_id=actor_id)


def reorder_artwork_slots(
    session: Session,
    *,
    exhibition_date: _dt.date,
    order: list[dict[str, Any]],
) -> dict[str, Any]:
    """순서 변경 (API 문서 §9.7). 12개 슬롯 전체를 돌려준다."""
    exhibition = find_exhibition(session, exhibition_date)
    artwork_admin_service.reorder(session, exhibition.id, order)
    ttl = media_service.url_ttl_seconds(session)
    return {"slots": artwork_admin_service.slots_of(session, exhibition.id, ttl_seconds=ttl)}


def _slot_result(
    session: Session,
    exhibition: Exhibition,
    position: int,
    *,
    today: _dt.date,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """발행 판정은 **모든 변경 경로의 마지막**에서 한 번 일어난다(백엔드 문서 §9)."""
    state = publishing.apply(session, exhibition, today=today, actor_id=actor_id)
    ttl = media_service.url_ttl_seconds(session)
    return {
        "slot": artwork_admin_service.slot_of(session, exhibition.id, position, ttl_seconds=ttl),
        "exhibition": exhibition_state(session, exhibition, state),
    }


def exhibition_state(
    session: Session, exhibition: Exhibition, state: publishing.PublishState
) -> dict[str, Any]:
    """그림 저장 응답에 함께 실리는 전시 상태 (API 문서 §9.5).

    프런트가 저장 후 전시를 다시 조회하지 않게 한다.
    """
    return {
        "version": exhibition.version,
        "can_publish": state.can_publish,
        "publish_blockers": state.blockers,
        "is_published": state.is_published,
        "published_now": state.published_now,
    }


# ── 숨김 ───────────────────────────────────────────────────────────────────


def hide(
    session: Session, *, exhibition_date: _dt.date, reason: str | None, today: _dt.date
) -> dict[str, Any]:
    """발행된 전시를 관람자에게서 감춘다. 유일한 철회 수단이다 (PRD §6.9)."""
    exhibition = _find(session, exhibition_date)
    if exhibition is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": exhibition_date.isoformat()})
    if not exhibition.is_published:
        raise AppError(ErrorCode.EXHIBITION_NOT_PUBLISHED)
    if exhibition.is_hidden:
        raise AppError(ErrorCode.EXHIBITION_ALREADY_HIDDEN)

    now = now_utc()
    q.update(
        session,
        Exhibition,
        where={"id": exhibition.id},
        values={"is_hidden": True, "hidden_at": now, "hidden_reason": normalize_text(reason)},
    )
    return _hide_response(session, exhibition_date, today, is_hidden=True, hidden_at=now)


def unhide(session: Session, *, exhibition_date: _dt.date, today: _dt.date) -> dict[str, Any]:
    exhibition = _find(session, exhibition_date)
    if exhibition is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": exhibition_date.isoformat()})
    if not exhibition.is_published:
        raise AppError(ErrorCode.EXHIBITION_NOT_PUBLISHED)

    q.update(
        session,
        Exhibition,
        where={"id": exhibition.id},
        values={"is_hidden": False, "hidden_at": None, "hidden_reason": None},
    )
    return _hide_response(session, exhibition_date, today, is_hidden=False, hidden_at=None)


def _hide_response(
    session: Session,
    exhibition_date: _dt.date,
    today: _dt.date,
    *,
    is_hidden: bool,
    hidden_at: _dt.datetime | None,
) -> dict[str, Any]:
    """`current_exhibition_date`는 조작 **후** 관람자에게 실제로 걸리는 전시의 발행일이다.

    큐레이터가 조작 결과를 즉시 확인할 수 있어야 한다(PRD §6.9).
    """
    from chalicelib.services import exhibition_service

    current = exhibition_service.find_current(session, today)
    return {
        "exhibition_date": format_date(exhibition_date),
        "is_hidden": is_hidden,
        "hidden_at": format_rfc3339(hidden_at),
        "current_exhibition_date": format_date(current.exhibition_date) if current else None,
    }


# ── 이어쓰기 ───────────────────────────────────────────────────────────────


def carry_draft(
    session: Session, *, from_date: _dt.date, today: _dt.date, actor_id: uuid.UUID | None
) -> dict[str, Any]:
    """과거 미발행일의 드래프트를 **오늘 날짜로 이동**한다. 복사가 아니다 (PRD 부록 B).

    12점 × 설명은 하루치 노동이고, 그것이 자정 한 번으로 잠기면 그 자체가 위험이다.
    """
    source = _find(session, from_date)
    if (
        source is None
        or source.is_published
        or not (normalize_text(source.title) or normalize_text(source.theme) or source.artwork_count > 0)
    ):
        raise AppError(ErrorCode.DRAFT_NOT_FOUND)

    target = _find(session, today)
    if target is not None and (
        normalize_text(target.title) or normalize_text(target.theme) or target.artwork_count > 0
    ):
        raise AppError(ErrorCode.DRAFT_TARGET_OCCUPIED, details={"target_date": today.isoformat()})

    moved = source.artwork_count
    now = now_utc()

    if target is None:
        # 원본 행의 날짜만 바꾼다 — 그림·이미지가 그대로 따라오고 이동이 원자적이 된다.
        q.update(
            session,
            Exhibition,
            where={"id": source.id},
            values={"exhibition_date": today, "draft_updated_at": now, "updated_at": now},
        )
        target_id = source.id
    else:
        # 오늘 날짜에 빈 행이 이미 있으면 그 행을 지우고 원본을 옮긴다.
        q.delete(session, Exhibition, where={"id": target.id})
        session.flush()
        q.update(
            session,
            Exhibition,
            where={"id": source.id},
            values={"exhibition_date": today, "draft_updated_at": now, "updated_at": now},
        )
        target_id = source.id

    moved_exhibition = q.fetch_one(session, Exhibition, where={"id": target_id})
    assert moved_exhibition is not None
    publishing.apply(session, moved_exhibition, today=today, actor_id=actor_id)

    return {
        "from_date": format_date(from_date),
        "to_date": format_date(today),
        "moved_artwork_count": moved,
        "exhibition": admin_detail(session, exhibition_date=today, today=today),
    }


# ── 홈 요약 ────────────────────────────────────────────────────────────────


def summary(session: Session, *, today: _dt.date) -> dict[str, Any]:
    """B 홈 요약 (API 문서 §9.1). PRD 부록 B가 지정한 두 숫자가 중심이다."""
    from sqlalchemy import func

    from chalicelib.db.models import AppUser, ViewLog
    from chalicelib.services import exhibition_service

    today_entrants = q.count(
        session,
        ViewLog,
        where={"viewed_on": today, "is_anonymized": False},
        distinct_on="user_id",
    )

    total_members = q.count(session, AppUser, where={"role": "viewer", "is_blocked": False})

    # 이번 주(월요일 기준) 3일 이상 입장한 회원. 회원 100명 규모에서는 그룹 결과를
    # 그대로 받아 세는 편이 HAVING 전용 질의를 따로 만드는 것보다 단순하다.
    monday = week_start(today)
    per_member = q.aggregate(
        session,
        ViewLog,
        values={"days": func.count(func.distinct(ViewLog.viewed_on))},
        group_by=["user_id"],
        where={"viewed_on__gte": monday, "viewed_on__lte": today, "is_anonymized": False},
    )
    weekly_active = sum(1 for row in per_member if row["user_id"] and row["days"] >= 3)

    pending_drafts = q.count(
        session,
        Exhibition,
        where=q.Q(is_published=False, exhibition_date__gte=today)
        & (q.Q(artwork_count__gt=0) | ~q.Q(title=None) | ~q.Q(theme=None)),
    )

    return {
        "today_entrant_count": today_entrants,
        "weekly_active_ratio": round(weekly_active / total_members, 3) if total_members else 0.0,
        "weekly_active_count": weekly_active,
        "total_member_count": total_members,
        "carried_over_days": exhibition_service.carried_over_days(session, today),
        "pending_draft_count": pending_drafts,
        "lead_time_days": _lead_time_days(session, today),
    }


def _lead_time_days(session: Session, today: _dt.date) -> int:
    """오늘부터 **연속으로** 발행 준비된 날 수 (PRD §3.2 사전 준비 리드타임)."""
    horizon = today + _dt.timedelta(days=30)
    published = {
        row["exhibition_date"]
        for row in q.fetch(
            session,
            Exhibition,
            where={
                "is_published": True,
                "is_hidden": False,
                "exhibition_date__gte": today,
                "exhibition_date__lte": horizon,
            },
            columns=["exhibition_date"],
        )
    }
    days = 0
    for day in date_range(today, horizon):
        if day not in published:
            break
        days += 1
    return days

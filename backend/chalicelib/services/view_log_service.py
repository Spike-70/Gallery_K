"""관람 기록 (DB 문서 §4.6·§4.7, API 문서 §7.4·§7.6).

두 기록 모두 UPSERT다. 중복 호출이 자연 멱등이므로 클라이언트의 재시도가 지표를
왜곡하지 않는다.

**실패해도 사용자에게 노출하지 않는다**(백엔드 문서 §9) — 기록이 안 된 것은 문제지만,
그 때문에 그림을 못 보게 되는 것이 더 큰 문제다. 호출부가 이 규칙을 지킨다.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy.orm import Session

from chalicelib.core.ids import new_id
from chalicelib.core.timeutil import now_utc
from chalicelib.db import query as q
from chalicelib.db.models import ArtworkViewLog, ViewLog


def record_entry(
    session: Session,
    *,
    user_id: uuid.UUID,
    viewed_on: _dt.date,
    exhibition_id: uuid.UUID,
) -> bool:
    """갤러리 입장. **관람일 기준 하루 1행**이며 두 번째부터는 카운터만 오른다.

    충돌 시 `exhibition_id`를 갱신하지 않는다 — 그날 처음 연 전시가 대표값이다.
    아카이브 진입도 같은 입장으로 센다(PRD §6.5).

    반환값은 '오늘 첫 입장인가'다.
    """
    now = now_utc()
    existed = q.exists(session, ViewLog, where={"user_id": user_id, "viewed_on": viewed_on})
    q.upsert(
        session,
        ViewLog,
        values={
            "id": new_id(),
            "user_id": user_id,
            "viewed_on": viewed_on,
            "exhibition_id": exhibition_id,
            "first_entered_at": now,
            "last_entered_at": now,
            "entry_count": 1,
            "created_at": now,
            "updated_at": now,
        },
        conflict=["user_id", "viewed_on"],
        update_values={
            "last_entered_at": now,
            "entry_count": ViewLog.entry_count + 1,
            "updated_at": now,
        },
    )
    return not existed


def record_artwork_view(
    session: Session,
    *,
    user_id: uuid.UUID,
    artwork_id: uuid.UUID,
    exhibition_id: uuid.UUID,
    viewed_on: _dt.date,
) -> int:
    """그림 열람. **(회원, 그림) 조합당 1행**이므로 중복 제거가 제약으로 표현된다.

    반환값은 이 전시에서 지금까지 열어본 그림 수다.
    """
    now = now_utc()
    q.upsert(
        session,
        ArtworkViewLog,
        values={
            "id": new_id(),
            "user_id": user_id,
            "artwork_id": artwork_id,
            "exhibition_id": exhibition_id,
            "first_viewed_on": viewed_on,
            "first_viewed_at": now,
            "last_viewed_at": now,
            "view_count": 1,
            "created_at": now,
            "updated_at": now,
        },
        conflict=["user_id", "artwork_id"],
        update_values={
            "last_viewed_at": now,
            "view_count": ArtworkViewLog.view_count + 1,
            "updated_at": now,
        },
    )
    return viewed_count(session, user_id=user_id, exhibition_id=exhibition_id)


def viewed_count(session: Session, *, user_id: uuid.UUID, exhibition_id: uuid.UUID) -> int:
    return q.count(session, ArtworkViewLog, where={"user_id": user_id, "exhibition_id": exhibition_id})


def viewed_counts_by_exhibition(
    session: Session, *, user_id: uuid.UUID, exhibition_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """아카이브 목록용. 전시마다 세면 N+1이므로 한 번의 집계로 끝낸다 (DB 문서 §7)."""
    if not exhibition_ids:
        return {}
    from sqlalchemy import func

    rows = q.aggregate(
        session,
        ArtworkViewLog,
        values={"viewed": func.count()},
        group_by=["exhibition_id"],
        where={"user_id": user_id, "exhibition_id__in": exhibition_ids},
    )
    return {row["exhibition_id"]: row["viewed"] for row in rows}


def record_entry_for_date(
    session: Session, *, user_id: uuid.UUID, exhibition_date: _dt.date, today: _dt.date
) -> dict[str, object] | None:
    """대상 전시를 확인하고 입장을 기록한다. 전시가 보이지 않으면 `None`."""
    from chalicelib.services import exhibition_service

    exhibition_id = exhibition_service.visible_exhibition_id(session, exhibition_date)
    if exhibition_id is None:
        return None
    is_first = record_entry(session, user_id=user_id, viewed_on=today, exhibition_id=exhibition_id)
    return {"viewed_on": today.isoformat(), "is_first_entry_today": is_first}

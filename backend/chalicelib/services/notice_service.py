"""휴관 공지 (DB 문서 §4.8, API 문서 §6.2·§9.18).

활성 공지의 기간 중첩을 DB가 막으므로 "오늘의 공지"는 항상 0건 또는 1건이다.
그 사실에 기대어 이 서비스는 분기를 두지 않는다.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import format_date
from chalicelib.db import query as q
from chalicelib.db.models import Notice


def serialize_notice(row: Notice) -> dict[str, Any]:
    """`NoticeItem` (API 문서 §3.7)."""
    return {
        "id": str(row.id),
        "starts_on": format_date(row.starts_on),
        "ends_on": format_date(row.ends_on),
        "body": row.body,
        "is_active": row.is_active,
    }


def current_notice(session: Session, today: _dt.date) -> dict[str, Any] | None:
    """오늘 유효한 공지. 없으면 `None`."""
    row = q.fetch_one(
        session,
        Notice,
        where={"is_active": True, "starts_on__lte": today, "ends_on__gte": today},
        order_by=["starts_on"],
    )
    return serialize_notice(row) if row else None


def is_notice_period(session: Session, day: _dt.date) -> bool:
    """공지 기간은 발행 빈도 지표의 분모와 큐레이터 연장 알림에서 제외된다."""
    return q.exists(
        session,
        Notice,
        where={"is_active": True, "starts_on__lte": day, "ends_on__gte": day},
    )


def list_notices(
    session: Session, *, include_past: bool, today: _dt.date, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    where: dict[str, Any] = {"is_active": True}
    if not include_past:
        where["ends_on__gte"] = today
    total = q.count(session, Notice, where=where)
    rows = q.fetch(session, Notice, where=where, order_by=["-starts_on"], limit=limit, offset=offset)
    return [serialize_notice(row) for row in rows], total


def create_notice(
    session: Session,
    *,
    starts_on: _dt.date,
    ends_on: _dt.date,
    body: str,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    _guard_period(session, starts_on, ends_on, exclude_id=None)
    row = q.insert(
        session,
        Notice,
        {
            "starts_on": starts_on,
            "ends_on": ends_on,
            "body": body,
            "is_active": True,
            "created_by": actor_id,
        },
    )
    return serialize_notice(row)


def update_notice(
    session: Session,
    notice_id: uuid.UUID,
    *,
    starts_on: _dt.date | None,
    ends_on: _dt.date | None,
    body: str | None,
) -> dict[str, Any]:
    row = q.fetch_one(session, Notice, where={"id": notice_id, "is_active": True})
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "notice"})

    new_start = starts_on or row.starts_on
    new_end = ends_on or row.ends_on
    _guard_period(session, new_start, new_end, exclude_id=notice_id)

    values: dict[str, Any] = {"starts_on": new_start, "ends_on": new_end}
    if body is not None:
        values["body"] = body
    q.update(session, Notice, where={"id": notice_id}, values=values)
    session.expire(row)
    refreshed = q.fetch_one(session, Notice, where={"id": notice_id})
    assert refreshed is not None
    return serialize_notice(refreshed)


def cancel_notice(session: Session, notice_id: uuid.UUID) -> None:
    """취소는 삭제가 아니라 비활성이다 — 무엇을 언제 걸었는지가 남는다."""
    affected = q.update(
        session, Notice, where={"id": notice_id, "is_active": True}, values={"is_active": False}
    )
    if affected == 0:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": "notice"})


def _guard_period(
    session: Session, starts_on: _dt.date, ends_on: _dt.date, *, exclude_id: uuid.UUID | None
) -> None:
    """사전 검사는 UX용이다. 최종 방어선은 EXCLUDE 제약이며 경쟁 조건도 그쪽이 막는다."""
    if ends_on < starts_on:
        raise AppError(ErrorCode.NOTICE_PERIOD_INVALID)
    where = q.Q(is_active=True, starts_on__lte=ends_on, ends_on__gte=starts_on)
    if exclude_id is not None:
        where = where & ~q.Q(id=exclude_id)
    conflict = q.fetch_one(session, Notice, where=where)
    if conflict is not None:
        raise AppError(ErrorCode.NOTICE_PERIOD_OVERLAP, details={"conflict_notice_id": str(conflict.id)})

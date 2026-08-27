"""통계 *(v1.1)* (API 문서 §9.19).

경로와 스키마를 MVP 시점에 확정한다 — 프런트엔드가 나중에 붙일 때 계약 협의를 다시
하지 않기 위함이다.

**미입장일도 행으로 포함한다.** 없는 날을 클라이언트가 채워 넣게 하면 "0인 날"과
"데이터가 없는 날"이 화면에서 구분되지 않는다.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.config.constants import STATS_MEMBER_SEARCH_LIMIT
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.timeutil import format_date
from chalicelib.db import query as q
from chalicelib.db.models import AppUser
from chalicelib.db.queries import stats as stats_queries
from chalicelib.utils.text import mask_phone, normalize_phone


def daily(session: Session, *, from_date: _dt.date, to_date: _dt.date) -> list[dict[str, Any]]:
    rows = stats_queries.fetch_daily(session, from_date=from_date, to_date=to_date)
    return [
        {
            "date": format_date(row["date"]),
            "exhibition_date": format_date(row["exhibition_date"]),
            "exhibition_title": row["exhibition_title"],
            "is_carried_over": bool(
                row["exhibition_date"] is not None and row["exhibition_date"] < row["date"]
            ),
            "entrant_count": row["entrant_count"],
            "artwork_view_count": row["artwork_view_count"],
        }
        for row in rows
    ]


def search_members(session: Session, *, query: str) -> list[dict[str, Any]]:
    """B-1의 이름/연락처 입력 후보 목록. 여기서는 **마스킹된 번호**만 나간다."""
    # 전화번호처럼 보일 때만 번호 완전일치를 조건에 더한다 — 자리표시자 값을 쓰지 않는다.
    digits = normalize_phone(query)
    match = q.Q(name__contains=query)
    if digits:
        match = match | q.Q(phone=digits)
    where = q.Q(role="viewer") & match
    rows = q.fetch(
        session,
        AppUser,
        where=where,
        order_by=["name"],
        limit=STATS_MEMBER_SEARCH_LIMIT,
        columns=["id", "name", "phone"],
    )
    if not rows:
        return []

    identifiers = [row["id"] for row in rows]
    last_seen = _last_viewed_map(session, identifiers)
    return [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "phone_masked": mask_phone(row["phone"]),
            "last_viewed_on": format_date(last_seen.get(row["id"])),
        }
        for row in rows
    ]


def _last_viewed_map(session: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, _dt.date]:
    """후보 전원의 마지막 입장일을 한 번의 집계로 가져온다 — 20건이어도 N+1을 만들지 않는다."""
    from sqlalchemy import func

    from chalicelib.db.models import ViewLog

    rows = q.aggregate(
        session,
        ViewLog,
        values={"last_viewed_on": func.max(ViewLog.viewed_on)},
        group_by=["user_id"],
        where={"user_id__in": user_ids, "is_anonymized": False},
    )
    return {row["user_id"]: row["last_viewed_on"] for row in rows}


def member_detail(
    session: Session, *, user_id: uuid.UUID, from_date: _dt.date, to_date: _dt.date
) -> dict[str, Any]:
    """`viewed_artwork_count / total_artwork_count`가 B-1-1의 `8 / 12` 표시 근거다."""
    user = q.fetch_one(session, AppUser, where={"id": user_id, "role": "viewer"})
    if user is None:
        raise AppError(ErrorCode.MEMBER_NOT_FOUND)

    rows = stats_queries.fetch_member_daily(session, user_id=user_id, from_date=from_date, to_date=to_date)
    return {
        "member": {
            "id": str(user.id),
            "name": user.name,
            "phone_masked": mask_phone(user.phone),
        },
        "days": [
            {
                "date": format_date(row["date"]),
                "exhibition_date": format_date(row["exhibition_date"]),
                "exhibition_title": row["exhibition_title"],
                "entered": bool(row["entered"]),
                "viewed_artwork_count": row["viewed_artwork_count"],
                "total_artwork_count": row["total_artwork_count"],
            }
            for row in rows
        ],
    }

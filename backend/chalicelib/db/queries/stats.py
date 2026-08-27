"""통계 집계 전용 질의 (DB 문서 §7, API 문서 §9.19).

기간별 그룹 집계다. 요청 범위의 **모든 날짜를 포함**해야 하므로 날짜 시리즈가 기준이고,
집계는 거기에 붙는다 — 데이터가 없는 날을 클라이언트가 채워 넣게 하지 않는다.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

_DAILY = text("""
WITH days AS (
    SELECT CAST(
        generate_series(CAST(:from_date AS date), CAST(:to_date AS date), interval '1 day') AS date
    ) AS day
)
SELECT
    days.day                                        AS date,
    hung.exhibition_date                            AS exhibition_date,
    hung.title                                      AS exhibition_title,
    coalesce(entrants.entrant_count, 0)             AS entrant_count,
    coalesce(views.artwork_view_count, 0)           AS artwork_view_count
FROM days
LEFT JOIN LATERAL (
    SELECT e.exhibition_date, e.title
    FROM exhibition e
    WHERE e.is_published AND NOT e.is_hidden AND e.exhibition_date <= days.day
    ORDER BY e.exhibition_date DESC
    LIMIT 1
) hung ON TRUE
LEFT JOIN LATERAL (
    SELECT count(DISTINCT v.user_id) AS entrant_count
    FROM view_log v
    WHERE v.viewed_on = days.day AND NOT v.is_anonymized
) entrants ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS artwork_view_count
    FROM artwork_view_log a
    WHERE a.first_viewed_on = days.day AND NOT a.is_anonymized
) views ON TRUE
ORDER BY days.day
""")

_MEMBER_DAILY = text("""
WITH days AS (
    SELECT CAST(
        generate_series(CAST(:from_date AS date), CAST(:to_date AS date), interval '1 day')  AS date
    ) AS day
)
SELECT
    days.day                                        AS date,
    hung.exhibition_date                            AS exhibition_date,
    hung.title                                      AS exhibition_title,
    (entry.entered IS NOT NULL)                     AS entered,
    coalesce(seen.viewed_artwork_count, 0)          AS viewed_artwork_count,
    coalesce(hung.artwork_count, 0)                 AS total_artwork_count
FROM days
LEFT JOIN LATERAL (
    SELECT e.exhibition_date, e.title, e.id, e.artwork_count
    FROM exhibition e
    WHERE e.is_published AND NOT e.is_hidden AND e.exhibition_date <= days.day
    ORDER BY e.exhibition_date DESC
    LIMIT 1
) hung ON TRUE
LEFT JOIN LATERAL (
    SELECT 1 AS entered
    FROM view_log v
    WHERE v.user_id = :user_id AND v.viewed_on = days.day
    LIMIT 1
) entry ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS viewed_artwork_count
    FROM artwork_view_log a
    WHERE a.user_id = :user_id AND a.exhibition_id = hung.id
) seen ON TRUE
ORDER BY days.day
""")


def fetch_daily(session: Session, *, from_date: _dt.date, to_date: _dt.date) -> list[dict[str, Any]]:
    result = session.execute(_DAILY, {"from_date": from_date, "to_date": to_date})
    return [dict(row) for row in result.mappings()]


def fetch_member_daily(
    session: Session, *, user_id: uuid.UUID, from_date: _dt.date, to_date: _dt.date
) -> list[dict[str, Any]]:
    result = session.execute(_MEMBER_DAILY, {"user_id": user_id, "from_date": from_date, "to_date": to_date})
    return [dict(row) for row in result.mappings()]

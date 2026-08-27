"""관리자 달력 전용 질의 (DB 문서 §7).

날짜 시리즈 각각에 대해 "그날 걸린 전시"를 1건씩 끌어오는 **측면 조인(LATERAL)**이다.
공용 헬퍼로는 표현되지 않고, 날짜별 반복 질의(N+1)를 금지하기 위해 여기에 격리한다.

`db/queries/`의 존재 이유는 이것 하나다 — 서비스에 SQL이 흩어지지 않게 하는 것.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

#: 날짜 시리즈 × (그 날짜의 전시 행, 그날 실제로 걸린 전시)
#: 파라미터 바인딩만 쓴다. 문자열 SQL 조립을 하지 않는다(백엔드 문서 §4.3).
_SQL = text("""
WITH days AS (
    -- `:param::date`는 SQLAlchemy의 text() 파서가 바인드로 보지 않는다. CAST를 쓴다.
    SELECT CAST(
        generate_series(CAST(:from_date AS date), CAST(:to_date AS date), interval '1 day') AS date
    ) AS day
)
SELECT
    days.day                        AS day,
    own.id                          AS own_id,
    own.title                       AS own_title,
    own.theme                       AS own_theme,
    own.is_published                AS own_is_published,
    own.is_hidden                   AS own_is_hidden,
    own.artwork_count               AS own_artwork_count,
    own.complete_artwork_count      AS own_complete_artwork_count,
    own.updated_at                  AS own_updated_at,
    own.draft_updated_at            AS own_draft_updated_at,
    hung.exhibition_date            AS hung_date,
    hung.title                      AS hung_title
FROM days
LEFT JOIN exhibition own
       ON own.exhibition_date = days.day
LEFT JOIN LATERAL (
    SELECT e.exhibition_date, e.title
    FROM exhibition e
    WHERE e.is_published
      AND NOT e.is_hidden
      AND e.exhibition_date <= days.day
    ORDER BY e.exhibition_date DESC
    LIMIT 1
) hung ON TRUE
ORDER BY days.day
""")


def fetch_calendar_rows(session: Session, *, from_date: _dt.date, to_date: _dt.date) -> list[dict[str, Any]]:
    result = session.execute(_SQL, {"from_date": from_date, "to_date": to_date})
    return [dict(row) for row in result.mappings()]

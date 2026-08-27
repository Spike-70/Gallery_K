"""회원 목록 전용 질의 (DB 문서 §7, 교차검토 X-25).

회원 행마다 **마지막 입장일**과 **푸시 상태**를 결합한다. 공용 헬퍼로 하면 회원 한 명당
두 번씩 질의하게 되고(N+1), 무엇보다 `last_viewed_on` 같은 **파생 필드로 정렬할 때는
계산이 페이징보다 앞서야** 하므로 한 질의 안에서 끝내야 한다.

파라미터 바인딩만 쓴다. 정렬 키는 화이트리스트에서 골라 SQL 조각으로 바꾼다 —
클라이언트 문자열이 SQL에 직접 들어가는 경로를 만들지 않는다.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

#: 허용 정렬 키 → ORDER BY 조각 (API 문서 §9.13). 목록 밖의 값은 라우트가 거부한다.
SORT_EXPRESSIONS: Final[dict[str, str]] = {
    "created_at": "u.created_at ASC",
    "-created_at": "u.created_at DESC",
    "name": "u.name ASC",
    "-name": "u.name DESC",
    "last_viewed_on": "last_viewed_on ASC NULLS LAST",
    "-last_viewed_on": "last_viewed_on DESC NULLS LAST",
}

_BASE = """
FROM app_user u
LEFT JOIN LATERAL (
    SELECT max(v.viewed_on) AS last_viewed_on
    FROM view_log v
    WHERE v.user_id = u.id AND NOT v.is_anonymized
) v ON TRUE
LEFT JOIN LATERAL (
    SELECT
        bool_or(p.is_active)                                        AS has_active,
        count(*)                                                    AS subscription_count,
        array_agg(DISTINCT p.platform)                              AS platforms
    FROM push_subscription p
    WHERE p.user_id = u.id
) p ON TRUE
-- NULL이 올 수 있는 파라미터는 타입을 명시한다. 그러지 않으면 PostgreSQL이
-- `$1`의 타입을 정하지 못한다(IndeterminateDatatype).
WHERE u.role = 'viewer'
  AND (CAST(:query AS text) IS NULL
       OR u.name ILIKE CAST(:name_pattern AS text) ESCAPE '\\'
       OR u.phone = CAST(:phone_exact AS varchar))
  AND (CAST(:status AS text) = 'all'
       OR (CAST(:status AS text) = 'active' AND NOT u.is_blocked)
       OR (CAST(:status AS text) = 'blocked' AND u.is_blocked))
  AND (CAST(:notify AS text) = 'all'
       OR (CAST(:notify AS text) = 'on' AND u.notify_enabled)
       OR (CAST(:notify AS text) = 'off' AND NOT u.notify_enabled))
"""

_SELECT = """
SELECT
    u.id, u.name, u.phone, u.role, u.created_at, u.created_via,
    u.is_blocked, u.blocked_at, u.notify_enabled, u.notify_at, u.last_login_at,
    v.last_viewed_on                       AS last_viewed_on,
    coalesce(p.subscription_count, 0)      AS subscription_count,
    coalesce(p.has_active, false)          AS has_active_subscription,
    p.platforms                            AS platforms
"""


def count_members(session: Session, *, filters: dict[str, Any]) -> int:
    statement = text(f"SELECT count(*) {_BASE}")
    return int(session.execute(statement, filters).scalar_one())


def fetch_members(
    session: Session, *, filters: dict[str, Any], sort: str, limit: int, offset: int
) -> list[dict[str, Any]]:
    order_by = SORT_EXPRESSIONS[sort]
    statement = text(f"{_SELECT}{_BASE} ORDER BY {order_by}, u.id LIMIT :limit OFFSET :offset")
    result = session.execute(statement, {**filters, "limit": limit, "offset": offset})
    return [dict(row) for row in result.mappings()]


def build_filters(*, query: str | None, status: str, notify: str) -> dict[str, Any]:
    """검색어는 **이름 부분일치 또는 전화번호 완전일치**다 (API 문서 §2.6)."""
    from chalicelib.db.query import escape_like
    from chalicelib.utils.text import normalize_phone

    return {
        "query": query,
        # `%`·`_`는 글자 그대로 다룬다. 공용 헬퍼와 같은 함수를 쓴다.
        "name_pattern": f"%{escape_like(query)}%" if query else None,
        "phone_exact": normalize_phone(query) if query else None,
        "status": status,
        "notify": notify,
    }

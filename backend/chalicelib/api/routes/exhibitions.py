"""관람자 전시 API (API 문서 §7.1–§7.4).

**조회는 부수효과를 갖지 않는다**(AP-4). 입장 기록은 별도 POST이며, 그래야 조회 응답이
캐시 가능해지고 PWA 오프라인 캐시가 성립한다.
"""

from __future__ import annotations

from chalicelib.config.constants import (
    ARCHIVE_DEFAULT_LIMIT,
    ARCHIVE_MAX_LIMIT,
    CACHE_EXHIBITION_BY_DATE,
    CACHE_EXHIBITION_CURRENT,
    CACHE_NO_STORE,
)
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import MEMBER, etag, paginated, require
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.logging import get_logger
from chalicelib.core.pagination import CURSOR, Cursor, CursorParams, cursor_meta
from chalicelib.core.timeutil import parse_date
from chalicelib.services import exhibition_service, media_service, setting_service, view_log_service
from chalicelib.services.setting_service import SettingKey

from ._base import blueprint, route

bp = blueprint(__name__)
logger = get_logger("exhibitions")


@route(bp, "/exhibitions/current")
@require(MEMBER)
@etag(cache_control=CACHE_EXHIBITION_CURRENT)
def current_exhibition() -> Result:
    """오늘 발행분이 없으면 **직전 발행 전시를 반환**하며, 이는 오류가 아니다(PRD §4.3)."""
    context = ctx_module.current()
    found = exhibition_service.current_detail(context.db, today=context.today, user_id=context.actor_id)
    if found is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_OPENED)
    data, tag = found
    return Result(data=data, etag=tag)


@route(bp, "/exhibitions")
@require(MEMBER)
@paginated(CURSOR, default_limit=ARCHIVE_DEFAULT_LIMIT, max_limit=ARCHIVE_MAX_LIMIT)
def archive(pagination: CursorParams) -> Result:
    """발행 전시만, 숨긴 전시 제외, 발행일 내림차순 (API 문서 §7.3)."""
    context = ctx_module.current()
    cursor = pagination.cursor
    rows, has_more, next_cursor = exhibition_service.list_archive(
        context.db,
        user_id=context.actor_id,
        limit=pagination.limit,
        cursor_key=str(cursor.key) if cursor else None,
        cursor_id=cursor.id if cursor else None,
        archive_size=setting_service.get_int(context.db, SettingKey.ARCHIVE_SIZE),
        ttl_seconds=media_service.url_ttl_seconds(context.db),
    )
    return Result(
        data={"exhibitions": rows},
        pagination=cursor_meta(
            limit=pagination.limit,
            count=len(rows),
            has_more=has_more,
            next_cursor=Cursor(key=next_cursor[0], id=next_cursor[1]).encode() if next_cursor else None,
        ),
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/exhibitions/{date}")
@require(MEMBER)
@etag(cache_control=CACHE_EXHIBITION_BY_DATE)
def exhibition_by_date(date: str) -> Result:
    """미발행·숨김·미래 날짜를 **모두 동일하게** 부재로 처리한다 (API 문서 §7.2)."""
    context = ctx_module.current()
    exhibition_date = parse_date(date)
    if exhibition_date is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": date})

    found = exhibition_service.detail_by_date(
        context.db,
        exhibition_date=exhibition_date,
        today=context.today,
        user_id=context.actor_id,
    )
    if found is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": date})
    data, tag = found
    return Result(data=data, etag=tag)


@route(bp, "/exhibitions/{date}/view", methods=("POST",))
@require(MEMBER)
def record_entry(date: str) -> Result:
    """관람일은 **서버가 결정**한다 (PRD §6.1). 아카이브 진입도 같은 입장으로 센다."""
    context = ctx_module.current()
    assert context.actor_id is not None
    exhibition_date = parse_date(date)
    if exhibition_date is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": date})

    recorded = view_log_service.record_entry_for_date(
        context.db,
        user_id=context.actor_id,
        exhibition_date=exhibition_date,
        today=context.today,
    )
    if recorded is None:
        raise AppError(ErrorCode.EXHIBITION_NOT_FOUND, details={"date": date})
    return Result(data=recorded, cache_control=CACHE_NO_STORE)

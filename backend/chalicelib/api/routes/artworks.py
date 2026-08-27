"""관람자 그림 API (API 문서 §7.5·§7.6).

라우트는 얇다 — 경로 변수를 해석하고, 서비스를 부르고, 부재를 오류로 바꾼다.
"""

from __future__ import annotations

import uuid

from chalicelib.config.constants import CACHE_EXHIBITION_BY_DATE, CACHE_NO_STORE
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import MEMBER, require
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import parse_uuid
from chalicelib.services import artwork_service

from ._base import blueprint, route

bp = blueprint(__name__)


def _artwork_uuid(artwork_id: str) -> uuid.UUID:
    parsed = parse_uuid(artwork_id)
    if parsed is None:
        # 형식이 아닌 ID도 부재로 답한다 — 형식 오류와 부재를 구분해 줄 이유가 없다.
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)
    return parsed


@route(bp, "/artworks/{artwork_id}")
@require(MEMBER)
def artwork_detail(artwork_id: str) -> Result:
    """미발행·숨김 전시의 그림도 동일하게 부재로 응답한다."""
    context = ctx_module.current()
    data = artwork_service.detail_response(
        context.db,
        artwork_id=_artwork_uuid(artwork_id),
        today=context.today,
        user_id=context.actor_id,
    )
    if data is None:
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)
    return Result(data=data, cache_control=CACHE_EXHIBITION_BY_DATE)


@route(bp, "/artworks/{artwork_id}/view", methods=("POST",))
@require(MEMBER)
def record_artwork_view(artwork_id: str) -> Result:
    """(회원, 그림) UPSERT이므로 중복 호출에 안전하다."""
    context = ctx_module.current()
    assert context.actor_id is not None
    viewed_count = artwork_service.record_view(
        context.db,
        artwork_id=_artwork_uuid(artwork_id),
        user_id=context.actor_id,
        today=context.today,
    )
    if viewed_count is None:
        raise AppError(ErrorCode.ARTWORK_NOT_FOUND)
    return Result(data={"viewed_artwork_count": viewed_count}, cache_control=CACHE_NO_STORE)

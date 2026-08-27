"""공개 API (API 문서 §6.1·§6.2).

비로그인 상태에서도 전시 제목이 보여야 한다(PRD §5.1). 그래서 두 경로 모두 `PUBLIC`이며,
인증 미들웨어는 세션이 있으면 채우고 없으면 그냥 통과시킨다.
"""

from __future__ import annotations

from chalicelib.config.constants import CACHE_LANDING
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import PUBLIC, require
from chalicelib.core.envelope import Result
from chalicelib.services import landing_service, notice_service

from ._base import blueprint, route

bp = blueprint(__name__)


@route(bp, "/public/landing")
@require(PUBLIC)
def landing() -> Result:
    """A 첫 화면 통합 조회. **이 엔드포인트는 실패하지 않는다.**"""
    context = ctx_module.current()
    # 요청 스코프 세션을 지연 생성으로 넘긴다 — DB에 닿지 못해도 화면은 뜬다.
    data = landing_service.build_landing(
        lambda: context.db,
        today=context.today,
        actor_id=context.actor_id,
        actor_role=context.actor_role,
    )
    return Result(data=data, cache_control=CACHE_LANDING)


@route(bp, "/public/notice")
@require(PUBLIC)
def current_notice() -> Result:
    """공지만 갱신 확인하는 경량 폴링 경로."""
    context = ctx_module.current()
    return Result(data={"notice": notice_service.current_notice(context.db, context.today)})

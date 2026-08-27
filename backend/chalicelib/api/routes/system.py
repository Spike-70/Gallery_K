"""시스템 API (API 문서 §10)."""

from __future__ import annotations

from chalicelib.config.constants import CACHE_NO_STORE
from chalicelib.core.decorators import PUBLIC, require
from chalicelib.core.envelope import Result
from chalicelib.services import health_service

from ._base import blueprint, route

bp = blueprint(__name__)


@route(bp, "/system/health")
@require(PUBLIC)
def health() -> Result:
    """`degraded`여도 HTTP 200을 반환한다.

    헬스 체크가 5xx를 내면 CloudFront 오리진 실패로 잡혀 A 첫 화면까지 죽는다(PRD §8.5).
    """
    return Result(data=health_service.check(), cache_control=CACHE_NO_STORE)

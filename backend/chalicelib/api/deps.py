"""조립 지점 (백엔드 문서 §5).

`core`의 미들웨어·데코레이터는 도메인을 모른다. 무엇을 할지는 알지만 **어떻게**는
주입받는다. 그 주입이 일어나는 곳이 여기 한 곳이다.

이 파일이 없으면 `core`가 `services`를 import 해야 하고, 계층 단방향 규칙이 무너진다.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from chalicelib.core import context as ctx_module
from chalicelib.core import decorators, middleware
from chalicelib.core.context import ActorSnapshot, MaintenanceState
from chalicelib.db import engine as engine_module
from chalicelib.services import audit_service, session_service, setting_service, throttle_service


def _maintenance_state() -> MaintenanceState:
    enabled, until = setting_service.maintenance_state()
    return MaintenanceState(enabled=enabled, until=until)


def _load_actor(session: Session, user_id: uuid.UUID) -> ActorSnapshot | None:
    return session_service.load_actor(session, user_id)


def _check_throttle(session: Session, scope: str, identifier: str) -> int:
    return throttle_service.remaining_lock_seconds(session, scope, identifier)


def _record_attempt(scope: str, identifier: str) -> int:
    return throttle_service.register_hit(scope, identifier)


def _record_audit(session: Session, action: str, context: ctx_module.RequestContext) -> None:
    """`@audited`가 성공한 요청에서 부른다.

    서비스가 처리 중에 `context.audit_entries`에 쌓아 둔 대상·요약을 함께 남긴다.
    쌓인 것이 없으면 액션만 남긴다 — 기록 자체가 빠지는 것보다 낫다.
    """
    entries: list[dict[str, Any]] = context.audit_entries or [{}]
    for entry in entries:
        audit_service.record(
            session,
            action=action,
            actor_id=context.actor_id,
            actor_role=context.actor_role,
            request_id=context.request_id,
            target_type=entry.get("target_type"),
            target_id=entry.get("target_id"),
            summary=entry.get("summary"),
            changes=entry.get("changes"),
        )


#: 소유권 판정 (백엔드 문서 §7 `@owns`). 자원 종류별로 등록한다.
#: 라우트 모듈이 자기 자원의 판정을 함께 들고 있고, 여기서 합친다.
def ownership_checks() -> dict[str, Any]:
    from chalicelib.api.routes import me

    return {**me.OWNERSHIP}


def _open_session() -> Session:
    """모듈 속성으로 한 번 더 돌아간다.

    함수 객체를 그대로 넘기면 등록 시점의 것이 박제되어 테스트가 세션을 바꿔치기할 수
    없다. 한 단계 우회가 통합 테스트를 가능하게 한다.
    """
    return engine_module.open_session()


def middleware_deps() -> middleware.MiddlewareDeps:
    return middleware.MiddlewareDeps(
        open_session=_open_session,
        maintenance_state=_maintenance_state,
        load_actor=_load_actor,
        session_ttl=session_service.session_ttl_seconds,
    )


def decorator_deps() -> decorators.DecoratorDeps:
    return decorators.DecoratorDeps(
        check_throttle=_check_throttle,
        record_attempt=_record_attempt,
        record_audit=_record_audit,
        ownership_checks=ownership_checks(),
    )


def install(app: Any) -> None:
    """앱 기동 시 1회. 미들웨어 등록과 데코레이터 주입을 함께 한다."""
    decorators.configure(decorator_deps())
    middleware.register(app, middleware_deps())

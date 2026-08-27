"""회원 API (API 문서 §8)."""

from __future__ import annotations

from chalicelib.config.constants import CACHE_NO_STORE
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import MEMBER, audited, body, current_request, owns, require
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import parse_uuid
from chalicelib.core.security import build_expired_session_cookie
from chalicelib.core.timeutil import parse_time_of_day
from chalicelib.schemas.me import PushSubscriptionIn, SettingsPatchIn, WithdrawIn
from chalicelib.services import member_service, push_service

from ._base import blueprint, route

bp = blueprint(__name__)

#: `@owns`가 참조하는 자원 이름. 오탈자를 막기 위해 상수로 둔다.
PUSH_SUBSCRIPTION = "push_subscription"


@route(bp, "/me")
@require(MEMBER)
def get_me() -> Result:
    context = ctx_module.current()
    assert context.actor_id is not None
    user = member_service.get_user(context.db, context.actor_id)
    return Result(data={"user": member_service.serialize_session_user(user)}, cache_control=CACHE_NO_STORE)


@route(bp, "/me/settings", methods=("PATCH",))
@require(MEMBER)
@body(SettingsPatchIn)
def patch_settings(payload: SettingsPatchIn) -> Result:
    context = ctx_module.current()
    assert context.actor_id is not None
    user = member_service.update_settings(
        context.db,
        context.actor_id,
        notify_enabled=payload.notify_enabled,
        notify_at=parse_time_of_day(payload.notify_at) if payload.notify_at else None,
        font_scale=payload.font_scale,
    )
    return Result(data={"user": user}, cache_control=CACHE_NO_STORE)


@route(bp, "/me", methods=("DELETE",))
@require(MEMBER)
@audited("member.withdraw")
@body(WithdrawIn)
def withdraw(payload: WithdrawIn) -> Result:
    """DB 문서 §10의 탈퇴 트랜잭션. 큐레이터 계정은 탈퇴할 수 없다."""
    context = ctx_module.current()
    assert context.actor_id is not None
    member_service.withdraw(context.db, context.actor_id)
    context.set_cookies.append(build_expired_session_cookie())

    # 감사 기록에는 액션 한 줄만 남는다. 행위자 식별자를 여기서 지우면 `@audited`가
    # actor 없는 행을 남기고, 그것이 DB 문서 §10이 요구하는 형태다.
    context.actor_id = None
    context.audit_entries.append({"summary": "회원 탈퇴"})
    return Result(data={}, cache_control=CACHE_NO_STORE)


@route(bp, "/me/push-subscriptions", methods=("POST",))
@require(MEMBER)
@body(PushSubscriptionIn)
def create_push_subscription(payload: PushSubscriptionIn) -> Result:
    context = ctx_module.current()
    assert context.actor_id is not None
    platform = payload.platform or push_service.detect_platform(current_request().headers.get("user-agent"))
    subscription, is_new = push_service.subscribe(
        context.db,
        context.actor_id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        platform=platform,
    )
    return Result(
        data={"subscription_id": subscription["id"], "is_new": is_new},
        status=201 if is_new else 200,
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/me/push-subscriptions")
@require(MEMBER)
def list_push_subscriptions() -> Result:
    """프런트가 브라우저의 실제 구독과 서버 등록 상태를 대조하는 데 쓴다."""
    context = ctx_module.current()
    assert context.actor_id is not None
    return Result(
        data={"subscriptions": push_service.list_subscriptions(context.db, context.actor_id)},
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/me/push-subscriptions/{subscription_id}", methods=("DELETE",))
@require(MEMBER)
@owns(PUSH_SUBSCRIPTION)
def delete_push_subscription(subscription_id: str) -> Result:
    context = ctx_module.current()
    assert context.actor_id is not None
    parsed = parse_uuid(subscription_id)
    if parsed is None:
        raise AppError(ErrorCode.NOT_FOUND, details={"resource": PUSH_SUBSCRIPTION})
    push_service.unsubscribe(context.db, context.actor_id, parsed)
    return Result(data={}, cache_control=CACHE_NO_STORE)


def _owns_push_subscription(
    session: object, context: ctx_module.RequestContext, kwargs: dict[str, object]
) -> bool:
    """소유가 아니면 **부재로 응답한다** — 남의 자원 ID로 존재를 떠보는 것을 막는다."""
    subscription_id = parse_uuid(str(kwargs.get("subscription_id", "")))
    if subscription_id is None or context.actor_id is None:
        return False
    return push_service.owns_subscription(session, context.actor_id, subscription_id)  # type: ignore[arg-type]


OWNERSHIP: dict[str, object] = {PUSH_SUBSCRIPTION: _owns_push_subscription}

"""인증 API (API 문서 §6.3–§6.9).

세션 토큰은 **HttpOnly 쿠키로만** 나간다. 응답 바디에 넣지 않는다(백엔드 문서 §13).
쿠키를 굽는 일은 `_issue_session`이 한 곳에서 한다.
"""

from __future__ import annotations

from chalicelib.config.constants import (
    CACHE_NO_STORE,
    RESET_CODE_TTL_SECONDS,
    THROTTLE_PASSWORD_RESET_RESEND_SECONDS,
)
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import MEMBER, PUBLIC, body, current_request, require, throttled
from chalicelib.core.envelope import Result
from chalicelib.core.security import build_expired_session_cookie, build_session_cookie, issue_session_token
from chalicelib.schemas.auth import (
    LoginIn,
    PasswordChangeIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    SignupIn,
)
from chalicelib.services import auth_service, member_service, session_service, throttle_service

from ._base import blueprint, route

bp = blueprint(__name__)


def _issue_session(result: auth_service.AuthenticatedUser) -> None:
    """세션 쿠키 발급의 단일 지점. 컨텍스트에 실으면 `response_finalize`가 붙인다."""
    context = ctx_module.current()
    ttl = session_service.session_ttl_seconds(context.db)
    token, _ = issue_session_token(
        user_id=result.id,
        role=result.role,
        token_version=result.token_version,
        issued_at=context.now,
        ttl_seconds=ttl,
    )
    context.set_cookies.append(build_session_cookie(token, max_age_seconds=ttl))
    context.actor_id = result.id
    context.actor_role = result.role
    context.token_version = result.token_version
    # 방금 발급했으므로 미들웨어가 다시 굽지 않게 한다.
    context.renew_session = False


def _client_ip() -> str:
    identity = (current_request().context or {}).get("identity") or {}
    return str(identity.get("sourceIp") or "unknown")


@route(bp, "/auth/signup", methods=("POST",))
@require(PUBLIC)
@body(SignupIn)
@throttled(throttle_service.SIGNUP, key=lambda _: _client_ip(), count_attempts=True)
def signup(payload: SignupIn) -> Result:
    """성공 `201`. 가입 완료 시 자동 로그인되어 C 갤러리로 직행한다."""
    context = ctx_module.current()
    result = auth_service.signup(
        context.db, phone=payload.phone, password=payload.password, name=payload.name
    )
    _issue_session(result)
    return Result(
        data={"user": result.user, "is_first_login": True},
        status=201,
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/auth/login", methods=("POST",))
@require(PUBLIC)
@body(LoginIn)
@throttled(throttle_service.LOGIN, key=lambda kwargs: kwargs["payload"].phone)
def login(payload: LoginIn) -> Result:
    """미가입·차단·오답을 구분하지 않는다 (API 문서 §5.2)."""
    context = ctx_module.current()
    result = auth_service.login(context.db, phone=payload.phone, password=payload.password)
    _issue_session(result)
    return Result(data={"user": result.user}, cache_control=CACHE_NO_STORE)


@route(bp, "/auth/logout", methods=("POST",))
@require(MEMBER)
def logout() -> Result:
    context = ctx_module.current()
    context.set_cookies.append(build_expired_session_cookie())
    return Result(data={}, cache_control=CACHE_NO_STORE)


@route(bp, "/auth/session")
@require(PUBLIC)
def session_info() -> Result:
    """앱 부팅 시 최초 1회. 비로그인이어도 200이다."""
    context = ctx_module.current()
    if not context.is_authenticated:
        return Result(data={"is_authenticated": False, "user": None}, cache_control=CACHE_NO_STORE)

    assert context.actor_id is not None
    user = member_service.get_user(context.db, context.actor_id)
    # 이 경로는 세션 확인이 목적이므로 남은 기간과 무관하게 쿠키를 갱신한다.
    context.renew_session = True
    return Result(
        data={
            "is_authenticated": True,
            "user": member_service.serialize_session_user(user),
        },
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/auth/password", methods=("POST",))
@require(MEMBER)
@body(PasswordChangeIn)
def change_password(payload: PasswordChangeIn) -> Result:
    """`token_version`이 증가하므로 현재 세션은 즉시 재발급되고 다른 단말은 무효화된다."""
    context = ctx_module.current()
    assert context.actor_id is not None
    result = auth_service.change_password(
        context.db,
        context.actor_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    _issue_session(result)
    return Result(data={"user": result.user}, cache_control=CACHE_NO_STORE)


@route(bp, "/auth/password/reset/request", methods=("POST",))
@require(PUBLIC)
@body(PasswordResetRequestIn)
@throttled(
    throttle_service.PASSWORD_RESET,
    key=lambda kwargs: kwargs["payload"].phone,
    count_attempts=True,
)
def request_password_reset(payload: PasswordResetRequestIn) -> Result:
    """*(v1.1)* 미가입 번호에도 **동일한 성공 응답**을 반환한다 (PRD §6.3)."""
    context = ctx_module.current()
    auth_service.request_password_reset(context.db, phone=payload.phone)
    return Result(
        data={
            "expires_in_seconds": RESET_CODE_TTL_SECONDS,
            "resend_after_seconds": THROTTLE_PASSWORD_RESET_RESEND_SECONDS,
        },
        cache_control=CACHE_NO_STORE,
    )


@route(bp, "/auth/password/reset/confirm", methods=("POST",))
@require(PUBLIC)
@body(PasswordResetConfirmIn)
@throttled(throttle_service.PASSWORD_RESET, key=lambda kwargs: kwargs["payload"].phone)
def confirm_password_reset(payload: PasswordResetConfirmIn) -> Result:
    """*(v1.1)* 자동 로그인하지 않는다. A-1으로 돌아가 새 비밀번호로 입장한다."""
    context = ctx_module.current()
    auth_service.confirm_password_reset(
        context.db, phone=payload.phone, code=payload.code, new_password=payload.new_password
    )
    return Result(data={}, cache_control=CACHE_NO_STORE)

"""인증 API (API 문서 §6.3–§6.9·§6.11–§6.15).

세션 토큰은 **HttpOnly 쿠키로만** 나간다. 응답 바디에 넣지 않는다(백엔드 문서 §13).
쿠키를 굽는 일은 `_issue_session`이 한 곳에서 한다.
"""

from __future__ import annotations

from typing import Any, Final

from chalice import Response

from chalicelib.config.constants import (
    CACHE_NO_STORE,
    OAUTH_LINK_COOKIE_NAME,
    OAUTH_STATE_COOKIE_NAME,
    RESET_CODE_TTL_SECONDS,
    THROTTLE_PASSWORD_RESET_RESEND_SECONDS,
)
from chalicelib.core import context as ctx_module
from chalicelib.core.decorators import MEMBER, PUBLIC, body, current_request, require, throttled
from chalicelib.core.envelope import Result
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.security import (
    build_expired_cookie,
    build_expired_session_cookie,
    build_session_cookie,
    issue_session_token,
    read_cookie,
    read_oauth_link_ticket,
    read_oauth_state_ticket,
)
from chalicelib.schemas.auth import (
    LoginIn,
    PasswordChangeIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    SignupIn,
    SocialLinkIn,
    SocialSignupIn,
)
from chalicelib.services import (
    auth_service,
    member_service,
    session_service,
    social_auth_service,
    throttle_service,
)

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


# ── 소셜 로그인 (API 문서 §6.11–§6.15, 소셜 문서 §3) ───────────────────────
#
# `start`·`callback` 둘은 **봉투 규약의 예외**다(API 문서 §2.2). 브라우저 주소창이
# 향하는 곳이므로 응답의 본체가 `Location` 헤더이며, 실패도 302로 끝난다 — JSON
# 오류 봉투를 내리면 사용자는 흰 화면의 영어 덩어리를 본다.

#: 리다이렉트 응답이 캐시되면 다음 로그인이 옛 `state`로 시작한다.
_REDIRECT_HEADERS: Final = {"Cache-Control": CACHE_NO_STORE}


def _redirect(location: str) -> Response:
    return Response(body="", status_code=302, headers={"Location": location, **_REDIRECT_HEADERS})


def _redirect_with_error(code: str) -> Response:
    """A-1으로 돌려보내며 코드를 실어 준다. 화면이 §5.2의 한국어 문구로 번역한다."""
    context = ctx_module.current()
    # 실패한 왕복의 흔적을 남기지 않는다. 재사용이 곧 리플레이다.
    context.set_cookies.append(build_expired_cookie(OAUTH_STATE_COOKIE_NAME))
    return _redirect(f"/login?social_error={code}")


def _oauth_cookie(name: str) -> str | None:
    return read_cookie(current_request().headers.get("cookie"), name)


def _link_ticket_or_error() -> Any:
    ticket = read_oauth_link_ticket(_oauth_cookie(OAUTH_LINK_COOKIE_NAME))
    if ticket is None:
        raise AppError(ErrorCode.SOCIAL_LINK_EXPIRED)
    return ticket


def _consume_link_cookie() -> None:
    """연결 티켓은 **1회용**이다. 성공하든 실패하든 지운다."""
    ctx_module.current().set_cookies.append(build_expired_cookie(OAUTH_LINK_COOKIE_NAME))


@route(bp, "/auth/social/providers")
@require(PUBLIC)
def social_providers() -> Result:
    """켜진 제공자만 나간다. **화면이 환경변수를 알 필요가 없다**(소셜 문서 §8)."""
    return Result(data={"providers": social_auth_service.list_providers()}, cache_control=CACHE_NO_STORE)


@route(bp, "/auth/social/{provider}/start")
@require(PUBLIC)
def social_start(provider: str) -> Response:
    """제공자 인가 화면으로 보낸다. **팝업이 아니라 리다이렉트다**(소셜 문서 SA-1)."""
    context = ctx_module.current()
    params = current_request().query_params or {}
    try:
        authorization = social_auth_service.begin(provider, next_path=params.get("next"))
    except AppError as error:
        return _redirect(f"/login?social_error={error.code}")

    context.set_cookies.append(authorization.state_cookie)
    return _redirect(authorization.authorize_url)


@route(bp, "/auth/social/{provider}/callback")
@require(PUBLIC)
def social_callback(provider: str) -> Response:
    """인가 코드를 받아 세션을 발급하거나 A-4 연결 화면으로 넘긴다."""
    context = ctx_module.current()
    params = current_request().query_params or {}
    ticket = read_oauth_state_ticket(_oauth_cookie(OAUTH_STATE_COOKIE_NAME))
    next_path = social_auth_service.safe_next_path(ticket.next_path if ticket else None)

    # 사용자가 동의 화면에서 그만둔 경우. 실패로 알리지 않는다 — 스스로 그만둔 것이다.
    if params.get("error"):
        context.set_cookies.append(build_expired_cookie(OAUTH_STATE_COOKIE_NAME))
        return _redirect("/login")

    code = params.get("code")
    if not code:
        return _redirect_with_error(ErrorCode.SOCIAL_STATE_INVALID)

    try:
        profile = social_auth_service.resolve_profile(
            provider, code=code, state=params.get("state"), ticket=ticket
        )
        authenticated = social_auth_service.find_linked_user(context.db, profile)
    except AppError as error:
        return _redirect_with_error(error.code)

    # 왕복이 끝났다. 대조용 쿠키는 여기서 수명을 다한다.
    context.set_cookies.append(build_expired_cookie(OAUTH_STATE_COOKIE_NAME))

    if authenticated is None:
        # 연결된 계정이 없다. **자동 가입하지 않는다** — 전화번호가 필요하다(SA-2).
        context.set_cookies.append(social_auth_service.build_link_cookie(profile, next_path=next_path))
        return _redirect("/auth/link")

    _issue_session(authenticated)
    return _redirect(next_path)


@route(bp, "/auth/social/link", methods=("POST",))
@require(PUBLIC)
@body(SocialLinkIn)
@throttled(throttle_service.LOGIN, key=lambda kwargs: kwargs["payload"].phone)
def social_link(payload: SocialLinkIn) -> Result:
    """A-4 `이미 회원이신가요?` — 비밀번호로 소유를 증명하고 연결한다(API 문서 §6.14)."""
    context = ctx_module.current()
    ticket = _link_ticket_or_error()
    result = social_auth_service.link_existing(
        context.db, ticket, phone=payload.phone, password=payload.password
    )
    _issue_session(result)
    _consume_link_cookie()
    return Result(data={"user": result.user}, cache_control=CACHE_NO_STORE)


@route(bp, "/auth/social/signup", methods=("POST",))
@require(PUBLIC)
@body(SocialSignupIn)
@throttled(throttle_service.SIGNUP, key=lambda _: _client_ip(), count_attempts=True)
def social_signup(payload: SocialSignupIn) -> Result:
    """A-4 `처음이신가요?` — 새 계정을 만들고 연결한다(API 문서 §6.15)."""
    context = ctx_module.current()
    ticket = _link_ticket_or_error()
    result = social_auth_service.signup_with_social(
        context.db, ticket, phone=payload.phone, name=payload.name
    )
    _issue_session(result)
    _consume_link_cookie()
    return Result(
        data={"user": result.user, "is_first_login": True},
        status=201,
        cache_control=CACHE_NO_STORE,
    )

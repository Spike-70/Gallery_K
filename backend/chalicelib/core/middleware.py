"""요청 파이프라인 (백엔드 문서 §6).

미들웨어를 **바깥에서 안쪽 순으로** 조립한다.

    1 request_context   2 access_log   3 error_boundary   4 maintenance_gate
    5 csrf_guard        6 db_session   7 authentication   8 response_finalize

로컬 개발용 CORS는 오류 경계 **바깥쪽**에 끼워 넣는다(§2.11). 안쪽에 두면 오류 응답에
CORS 헤더가 붙지 않고, 그러면 브라우저가 본문을 읽지 못해 개발자가 원인을 알 수 없다.
프리플라이트도 점검 모드와 무관하게 답해야 하므로 그 위치가 맞다.

순서의 근거 — 오류 경계가 인증보다 바깥이어야 인증 실패도 봉투로 나간다. 인증이 DB를
읽으므로 세션이 그보다 바깥에 있어야 하며, 세션 없이 끝나는 요청이 커넥션을 점유하지
않도록 지연 생성한다(교차검토 X-14).

**프레임워크 제약 하나** — Chalice는 뷰에서 나온 예외를 미들웨어보다 안쪽에서
500 응답으로 삼킨다. 그래서 뷰 경계의 예외 변환은 `decorators.endpoint`가 수행하고,
여기 `error_boundary`는 미들웨어 자신(인증·CSRF·점검)에서 난 예외를 맡는다.
변환 로직 자체는 `errors.translate_exception` 하나뿐이다.

도메인을 아는 동작(설정 읽기·회원 조회·세션 열기)은 **주입받는다.** core가 services를
import 하지 않기 위해서이며, 조립은 `api/deps.py`가 한다.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from chalice import Response

from chalicelib.config.constants import (
    CACHE_NO_STORE,
    CSRF_HEADER_NAME,
    CSRF_HEADER_VALUE,
    MUTATING_METHODS,
    REQUEST_ID_HEADER,
    SECURITY_HEADERS,
    SESSION_COOKIE_NAME,
)
from chalicelib.config.settings import settings
from chalicelib.core import context as ctx_module
from chalicelib.core.context import ActorSnapshot, MaintenanceState
from chalicelib.core.envelope import Result, error_body, success_body
from chalicelib.core.errors import AppError, ErrorCode, translate_exception
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.security import (
    build_expired_session_cookie,
    build_session_cookie,
    decode_session_token,
    issue_session_token,
    read_cookie,
)
from chalicelib.core.timeutil import format_rfc3339, now_utc

logger = get_logger("http")

#: 점검 모드에서도 열어 두는 경로. 첫 화면과 헬스 체크는 언제나 떠야 한다(PRD §8.5).
MAINTENANCE_ALLOWED_PREFIXES: Final = ("/public", "/system")

#: 운영 데이터는 캐시하지 않는다 (API 문서 §2.9).
ADMIN_PATH_PREFIX: Final = "/admin"


@dataclass(frozen=True, slots=True)
class MiddlewareDeps:
    """도메인을 아는 동작의 주입 지점."""

    open_session: Callable[[], Any]
    maintenance_state: Callable[[], MaintenanceState]
    load_actor: Callable[[Any, uuid.UUID], ActorSnapshot | None]
    #: 세션 수명(초). 운영 설정에서 온다.
    session_ttl: Callable[[Any], int]


def _json_response(body: dict[str, Any], status: int, headers: dict[str, str]) -> Response:
    return Response(body=body, status_code=status, headers={"Content-Type": "application/json", **headers})


def error_response(error: AppError, context: ctx_module.RequestContext) -> Response:
    """오류 봉투 조립의 단일 지점. 라우트 경계와 미들웨어가 함께 쓴다."""
    headers: dict[str, str] = {}
    if error.code in {ErrorCode.RATE_LIMITED, ErrorCode.AUTH_TOO_MANY_ATTEMPTS}:
        retry_after = (error.details or {}).get("retry_after_seconds")
        if retry_after is not None:
            headers["Retry-After"] = str(int(retry_after))
    return _json_response(
        error_body(error, context, include_doc_hint=not settings.is_production),
        error.status,
        headers,
    )


def success_response(result: Result, context: ctx_module.RequestContext) -> Response:
    return _json_response(
        success_body(result.data, context, pagination=result.pagination),
        result.status,
        dict(result.headers or {}),
    )


# ── 1. request_context ─────────────────────────────────────────────────────


def request_context(event: Any, get_response: Callable[[Any], Response]) -> Response:
    """요청 ID 발급, 시작 시각·KST 오늘 계산. 요청 내내 이 값들이 바뀌지 않는다."""
    path = (event.context or {}).get("path") or event.path
    context = ctx_module.new_context(method=event.method, path=path)
    token = ctx_module.bind(context)
    try:
        response = get_response(event)
    finally:
        ctx_module.unbind(token)
    response.headers[REQUEST_ID_HEADER] = context.request_id
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


# ── 2. access_log ──────────────────────────────────────────────────────────


def access_log(event: Any, get_response: Callable[[Any], Response]) -> Response:
    context = ctx_module.current()
    log_event(logger, "request.start", level=logging.DEBUG)
    response = get_response(event)
    duration_ms = int((now_utc() - context.now).total_seconds() * 1000)
    log_event(
        logger,
        "request.end",
        level=logging.INFO if response.status_code < 500 else logging.ERROR,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ── 3. error_boundary ──────────────────────────────────────────────────────


def error_boundary(event: Any, get_response: Callable[[Any], Response]) -> Response:
    """미들웨어에서 난 예외를 표준 봉투로 바꾼다. 인증 실패도 봉투로 나간다."""
    context = ctx_module.current()
    try:
        return get_response(event)
    # 경계이므로 전부 받는다 — 어떤 예외도 봉투 밖으로 나가지 않는다.
    except Exception as exc:
        context.rollback_only = True
        error = translate_exception(exc)
        if error.status >= 500:
            logger.exception("unhandled error in middleware", extra={"event": "request.error"})
        else:
            log_event(logger, "request.rejected", level=logging.WARNING, code=error.code)
        return error_response(error, context)


# ── 4. maintenance_gate ────────────────────────────────────────────────────


def make_maintenance_gate(deps: MiddlewareDeps) -> Callable[[Any, Callable[[Any], Response]], Response]:
    def maintenance_gate(event: Any, get_response: Callable[[Any], Response]) -> Response:
        context = ctx_module.current()
        if context.path.startswith(MAINTENANCE_ALLOWED_PREFIXES):
            return get_response(event)
        state = deps.maintenance_state()
        if state.enabled:
            raise AppError(ErrorCode.MAINTENANCE_MODE, details={"until": state.until})
        return get_response(event)

    return maintenance_gate


# ── 5. csrf_guard ──────────────────────────────────────────────────────────


def dev_cors(event: Any, get_response: Callable[[Any], Response]) -> Response:
    """로컬 개발 전용 CORS 응답 헤더 (API 문서 §2.11).

    프로덕션은 CloudFront 단일 배포에서 `/api/*`만 API Gateway로 보내므로 **동일 오리진**
    이고 프리플라이트가 발생하지 않는다. 로컬에서만 프런트(`localhost:5173`)가 다른
    포트에 있으므로, 그때만 허용 오리진을 명시하고 `credentials`를 켠다.

    **프리플라이트는 여기서 다루지 않는다** — OPTIONS는 애플리케이션 미들웨어보다 앞에서
    끝나며(`chalice local`도 API Gateway도), 그쪽은 `app.py`의 `CORSConfig`가 맡는다.
    이 미들웨어가 맡는 것은 **모든 응답에 헤더를 붙이는 일**이고, 특히 미들웨어 단계에서
    끝난 오류 응답이 그 대상이다. 그 응답에는 Chalice의 CORS 처리가 닿지 않는다.

    설정이 비어 있으면(=프로덕션) 아무 헤더도 붙이지 않는다 — 실수로 프로덕션에서
    교차 출처가 열리는 경로를 만들지 않는다.
    """
    origin = settings.dev_cors_origin
    if not origin:
        return get_response(event)

    response = get_response(event)
    for name, value in _cors_headers(origin).items():
        response.headers.setdefault(name, value)
    return response


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        # 세션 쿠키가 오가야 하므로 반드시 필요하다.
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": f"Content-Type, {CSRF_HEADER_NAME}, If-None-Match",
        "Access-Control-Expose-Headers": f"{REQUEST_ID_HEADER}, ETag, Retry-After",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


def csrf_guard(event: Any, get_response: Callable[[Any], Response]) -> Response:
    """`SameSite=Lax` + 변경 요청의 커스텀 헤더. 헤더가 없으면 처리하지 않는다."""
    if event.method in MUTATING_METHODS and event.headers.get(CSRF_HEADER_NAME) != CSRF_HEADER_VALUE:
        raise AppError(ErrorCode.CSRF_HEADER_MISSING)
    return get_response(event)


# ── 6. db_session ──────────────────────────────────────────────────────────


def make_db_session(deps: MiddlewareDeps) -> Callable[[Any, Callable[[Any], Response]], Response]:
    def db_session(event: Any, get_response: Callable[[Any], Response]) -> Response:
        """요청당 세션 1개·트랜잭션 1개. **커밋은 이 미들웨어의 책임이다.**

        서비스는 세션을 받되 스스로 커밋하지 않는다(백엔드 문서 §4.4).
        """
        context = ctx_module.current()
        context.session_factory = deps.open_session
        try:
            response = get_response(event)
        except BaseException:
            _finish_session(context, commit=False)
            raise
        # 라우트 경계가 예외를 봉투로 바꿨다면 정상 반환처럼 보인다. 상태 코드로 판정한다.
        commit = not context.rollback_only and response.status_code < 400
        _finish_session(context, commit=commit)
        return response

    return db_session


def _finish_session(context: ctx_module.RequestContext, *, commit: bool) -> None:
    if not context.has_session:
        return
    session = context.db
    try:
        if commit:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()
        context.reset_session()


# ── 7. authentication ──────────────────────────────────────────────────────


def make_authentication(deps: MiddlewareDeps) -> Callable[[Any, Callable[[Any], Response]], Response]:
    def authentication(event: Any, get_response: Callable[[Any], Response]) -> Response:
        """세션 쿠키 검증·무효화 카운터 대조·슬라이딩 갱신.

        **여기서는 권한을 판정하지 않는다.** 미인증도 그대로 통과시키고, 등급 강제는
        `@require`가 한다 — 공개 경로가 세션 유무를 알아야 하기 때문이다(`/public/landing`).
        """
        context = ctx_module.current()
        token = read_cookie(event.headers.get("cookie"), SESSION_COOKIE_NAME)
        if not token:
            return get_response(event)

        try:
            claims = decode_session_token(token)
        except AppError:
            # 깨진·만료된 쿠키는 비로그인으로 취급한다. 공개 경로가 401로 죽으면 안 된다.
            context.clear_session = True
            return get_response(event)

        actor = deps.load_actor(context.db, claims.user_id)
        if actor is None or actor.token_version != claims.token_version:
            # 무효화 카운터 불일치 = 비밀번호 변경·초기화로 끊긴 세션
            context.clear_session = True
            context.auth_error = (
                ErrorCode.AUTH_SESSION_REVOKED if actor is not None else ErrorCode.AUTH_REQUIRED
            )
            return get_response(event)

        context.actor_id = actor.id
        context.actor_role = actor.role
        context.token_version = actor.token_version
        context.renew_session = claims.needs_renewal
        return get_response(event)

    return authentication


# ── 8. response_finalize ───────────────────────────────────────────────────


def make_response_finalize(deps: MiddlewareDeps) -> Callable[[Any, Callable[[Any], Response]], Response]:
    def response_finalize(event: Any, get_response: Callable[[Any], Response]) -> Response:
        return _finalize(event, get_response, deps)

    return response_finalize


def _finalize(event: Any, get_response: Callable[[Any], Response], deps: MiddlewareDeps) -> Response:
    """봉투 `meta` 채우기, 캐시 헤더·쿠키 부착.

    라우트가 `Result`를 돌려주면 여기서 봉투가 된다. 이미 `Response`면 그대로 둔다
    (라우트 경계가 오류·`304`를 직접 만든 경우다).
    """
    context = ctx_module.current()
    response = get_response(event)

    body = response.body
    if isinstance(body, dict) and set(body) == {"Code", "Message"}:
        # Chalice가 직접 만든 오류(존재하지 않는 경로·메서드·미디어 타입). 프로덕션에서는
        # API Gateway가 먼저 걸러 내지만, 봉투 규약에 예외를 두지 않는다.
        return error_response(_from_framework_error(str(body["Code"])), context)
    if isinstance(body, Result):
        response = success_response(body, context)
        if body.cache_control:
            response.headers["Cache-Control"] = body.cache_control
        if body.etag:
            response.headers["ETag"] = body.etag

    if context.cache_control and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = context.cache_control

    # 관리자 전 API는 캐시하지 않는다 (API 문서 §2.9). 라우트가 아니라 여기서 못박는
    # 이유는 오류 응답과 새로 추가되는 라우트까지 예외 없이 덮기 위해서다.
    if context.path.startswith(ADMIN_PATH_PREFIX):
        response.headers["Cache-Control"] = CACHE_NO_STORE
    for name, value in context.extra_headers.items():
        response.headers.setdefault(name, value)

    _attach_session_cookie(context, response, deps)
    return response


#: Chalice 프레임워크 오류 → 카탈로그 코드. 없는 값은 내부 오류로 떨어진다.
_FRAMEWORK_ERROR_CODES: Final[dict[str, str]] = {
    "MethodNotAllowedError": ErrorCode.NOT_FOUND,
    "NotFoundError": ErrorCode.NOT_FOUND,
    "UnsupportedMediaType": ErrorCode.VALIDATION_FAILED,
    "BadRequest": ErrorCode.VALIDATION_FAILED,
    "BadRequestError": ErrorCode.VALIDATION_FAILED,
    "RequestEntityTooLarge": ErrorCode.UPLOAD_FILE_TOO_LARGE,
}


def _from_framework_error(code: str) -> AppError:
    return AppError(_FRAMEWORK_ERROR_CODES.get(code, ErrorCode.SYSTEM_INTERNAL))


def _attach_session_cookie(
    context: ctx_module.RequestContext, response: Response, deps: MiddlewareDeps
) -> None:
    cookies = list(context.set_cookies)
    if context.clear_session and not cookies:
        cookies.append(build_expired_session_cookie())
    elif context.renew_session and context.actor_id and context.actor_role:
        ttl = deps.session_ttl(context.db)
        token, expires_at = issue_session_token(
            user_id=context.actor_id,
            role=context.actor_role,
            token_version=context.token_version or 0,
            issued_at=context.now,
            ttl_seconds=ttl,
        )
        cookies.append(build_session_cookie(token, max_age_seconds=ttl))
        log_event(logger, "session.renewed", level=logging.DEBUG, expires_at=format_rfc3339(expires_at))
    if cookies:
        existing = response.headers.get("Set-Cookie")
        if isinstance(existing, list):
            response.headers["Set-Cookie"] = [*existing, *cookies]
        elif existing:
            response.headers["Set-Cookie"] = [existing, *cookies]
        else:
            response.headers["Set-Cookie"] = cookies if len(cookies) > 1 else cookies[0]


def register(app: Any, deps: MiddlewareDeps) -> None:
    """바깥→안쪽 순으로 등록한다. 이 순서가 곧 문서 §6의 표다."""
    app.register_middleware(request_context, "http")
    app.register_middleware(access_log, "http")
    app.register_middleware(dev_cors, "http")
    app.register_middleware(error_boundary, "http")
    app.register_middleware(make_maintenance_gate(deps), "http")
    app.register_middleware(csrf_guard, "http")
    app.register_middleware(make_db_session(deps), "http")
    app.register_middleware(make_authentication(deps), "http")
    app.register_middleware(make_response_finalize(deps), "http")

"""라우트 데코레이터 (백엔드 문서 §7).

라우트별 관심사는 전부 여기로 흡수한다. **라우트 본문에 권한·검증·기록 코드를 쓰지 않는다.**

데코레이터는 동작이면서 **선언적 메타데이터**다. 각 데코레이터는 뷰 함수에
`__gk_route_meta__`를 남기고, 계약 테스트가 전 라우트를 순회해 권한 데코레이터 누락을
검출한다(§12).

도메인을 아는 동작(시도 제한·감사 기록·소유권 판정)은 `configure()`로 주입받는다 —
core가 services를 import 하지 않기 위해서다.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final, Literal, TypeVar

from chalice import Response

from chalicelib.core import context as ctx_module
from chalicelib.core.envelope import NotModified, Result
from chalicelib.core.errors import (
    AppError,
    ErrorCode,
    FieldError,
    FieldErrorCode,
    field_errors_from_pydantic,
    translate_exception,
)
from chalicelib.core.logging import get_logger
from chalicelib.core.pagination import (
    CURSOR,
    Cursor,
    CursorParams,
    PageParams,
    PaginationMode,
    clamp_limit,
    parse_page,
)

logger = get_logger("route")

F = TypeVar("F", bound=Callable[..., Any])

AccessLevel = Literal["PUBLIC", "MEMBER", "CURATOR"]
PUBLIC: Final[AccessLevel] = "PUBLIC"
MEMBER: Final[AccessLevel] = "MEMBER"
CURATOR: Final[AccessLevel] = "CURATOR"

META_ATTRIBUTE: Final = "__gk_route_meta__"


@dataclass(slots=True)
class RouteMeta:
    """선언부에서 눈으로 보이는 것들. 계약 테스트가 이것을 읽는다."""

    access: AccessLevel | None = None
    audited_action: str | None = None
    throttle_scope: str | None = None
    paginated: PaginationMode | None = None
    body_schema: type | None = None
    query_schema: type | None = None
    owns_resource: str | None = None
    etag_enabled: bool = False


def meta_of(func: Callable[..., Any]) -> RouteMeta:
    existing = getattr(func, META_ATTRIBUTE, None)
    if existing is None:
        existing = RouteMeta()
        setattr(func, META_ATTRIBUTE, existing)
    return existing


def _carry_meta(source: Callable[..., Any], target: Callable[..., Any]) -> None:
    setattr(target, META_ATTRIBUTE, meta_of(source))


# ── 주입 지점 ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class DecoratorDeps:
    """도메인을 아는 동작. `api/deps.py`가 조립한다."""

    #: (scope, identifier) → 남은 잠금 초. 0이면 통과
    check_throttle: Callable[[Any, str, str], int] = field(default=lambda session, scope, identifier: 0)
    #: 시도를 누적하고 잠기면 남은 초를 돌려준다. 요청 트랜잭션과 무관하게 남아야 한다.
    record_attempt: Callable[[str, str], int] = field(default=lambda scope, identifier: 0)
    #: 성공한 변경 조작을 감사 로그로 남긴다
    record_audit: Callable[[Any, str, ctx_module.RequestContext], None] = field(
        default=lambda session, action, context: None
    )
    #: 자원 소유권 판정. 자원 종류별 판정 함수
    ownership_checks: dict[str, Callable[[Any, ctx_module.RequestContext, dict[str, Any]], bool]] = field(
        default_factory=dict
    )


_deps = DecoratorDeps()


def configure(deps: DecoratorDeps) -> None:
    global _deps
    _deps = deps


# ── 경계 ───────────────────────────────────────────────────────────────────


def endpoint[T: Callable[..., Any]](func: T) -> T:
    """라우트 경계.

    Chalice가 뷰의 예외를 미들웨어보다 안쪽에서 삼키므로(500 고정), 예외 → 봉투 변환을
    여기서 한다. 변환 규칙 자체는 `errors.translate_exception` 하나뿐이다.
    """
    from chalicelib.core.middleware import error_response  # 순환 import 회피

    @functools.wraps(func)
    def wrapper(**kwargs: Any) -> Any:
        context = ctx_module.current()
        try:
            result = func(**kwargs)
        except NotModified as signal:
            headers: dict[str, str | list[str]] = {"ETag": signal.etag}
            if signal.cache_control:
                headers["Cache-Control"] = signal.cache_control
            # 봉투 규약의 유일한 예외 — 본문이 비어 있다 (API 문서 §2.9)
            return Response(body="", status_code=304, headers=headers)
        except Exception as exc:
            context.rollback_only = True
            error = translate_exception(exc)
            if error.status >= 500:
                logger.exception("unhandled error in route", extra={"event": "route.error"})
            return error_response(error, context)

        if isinstance(result, Result | Response):
            return result
        return Result(data=result)

    _carry_meta(func, wrapper)
    return wrapper  # type: ignore[return-value]


# ── @require ───────────────────────────────────────────────────────────────


def require(level: AccessLevel) -> Callable[[F], F]:
    """권한 등급 강제. 선언부에서 권한이 눈으로 보인다.

    관리자 엔드포인트에 회원이 접근하면 `404`가 아니라 `403`이다 — 폐쇄형 서비스이고
    회원은 이미 신뢰 관계 안에 있으므로 존재를 숨길 이유가 없다(API 문서 §2.7).
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            context = ctx_module.current()
            if level != PUBLIC:
                if not context.is_authenticated:
                    raise AppError(context.auth_error or ErrorCode.AUTH_REQUIRED)
                if level == CURATOR and not context.is_curator:
                    raise AppError(ErrorCode.AUTH_FORBIDDEN)
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).access = level
        return wrapper  # type: ignore[return-value]

    return decorator


# ── @owns ──────────────────────────────────────────────────────────────────


def owns(resource: str) -> Callable[[F], F]:
    """대상 자원이 요청자 소유인지 검증한다(본인 구독 해제 등).

    등급으로 표현되지 않는 소유권 판정을 라우트마다 반복하지 않기 위해 존재한다.
    소유가 아니면 **부재로 응답한다** — 남의 자원 ID를 넣어 존재를 떠보는 것을 막는다.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            context = ctx_module.current()
            check = _deps.ownership_checks.get(resource)
            if check is None:
                raise RuntimeError(f"소유권 판정이 등록되지 않았습니다: {resource}")
            if not check(context.db, context, kwargs):
                raise AppError(ErrorCode.NOT_FOUND, details={"resource": resource})
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).owns_resource = resource
        return wrapper  # type: ignore[return-value]

    return decorator


# ── @body / @query ─────────────────────────────────────────────────────────


def body(schema: type) -> Callable[[F], F]:
    """요청 바디 파싱·검증. 실패 시 필드 오류를 자동 생성한다."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            raw = _read_json_body(current_request())
            kwargs["payload"] = _validate(schema, raw, source="body")
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).body_schema = schema
        return wrapper  # type: ignore[return-value]

    return decorator


def query(schema: type) -> Callable[[F], F]:
    """쿼리 파라미터 파싱·검증.

    미지원 파라미터는 무시하지 않고 `QUERY_UNKNOWN_PARAM`으로 거부한다 — 오타로 필터가
    조용히 풀리는 사고를 막는다(API 문서 §2.6).

    `sort`는 스키마 검증에 맡기지 않고 **먼저** 확인한다. 문서가 정렬 오류에 전용 코드와
    `details.allowed[]`를 요구하기 때문이다(§2.6) — 다른 필드와 같은 422로 뭉뚱그리면
    클라이언트가 "무엇이 허용되는가"를 알 수 없다.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            params = dict(current_request().query_params or {})
            # 페이지네이션 파라미터는 `@paginated`가 이미 소비했다.
            for reserved in ("limit", "cursor", "page"):
                params.pop(reserved, None)
            _guard_sort(schema, params)
            kwargs["params"] = _validate(schema, params, source="query")
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).query_schema = schema
        return wrapper  # type: ignore[return-value]

    return decorator


def current_request() -> Any:
    """Chalice 요청 객체 접근 지점. 요청 밖에서 부르면 프로그래밍 오류다."""
    from app import app as chalice_app

    request = chalice_app.current_request
    if request is None:
        raise RuntimeError("요청 컨텍스트 밖에서 요청 객체에 접근했습니다")
    return request


SORT_FIELD: Final = "sort"


def allowed_sort_values(schema: type) -> list[str] | None:
    """스키마의 `sort` 필드가 선언한 허용 목록. 선언이 없으면 None."""
    from typing import get_args

    field = getattr(schema, "model_fields", {}).get(SORT_FIELD)
    if field is None:
        return None
    values = [value for value in get_args(field.annotation) if isinstance(value, str)]
    return values or None


def _guard_sort(schema: type, params: dict[str, Any]) -> None:
    allowed = allowed_sort_values(schema)
    requested = params.get(SORT_FIELD)
    if allowed is None or requested is None or requested in allowed:
        return
    raise AppError(ErrorCode.QUERY_INVALID_SORT, details={"allowed": allowed})


def _read_json_body(request: Any) -> dict[str, Any]:
    from chalice import BadRequestError

    try:
        parsed = request.json_body
    except BadRequestError as exc:
        raise AppError(
            ErrorCode.VALIDATION_FAILED,
            field_errors=[FieldError("", FieldErrorCode.INVALID_FORMAT, "요청 형식이 올바르지 않습니다.")],
        ) from exc
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise AppError(
            ErrorCode.VALIDATION_FAILED,
            field_errors=[FieldError("", FieldErrorCode.INVALID_FORMAT, "요청 본문이 올바르지 않습니다.")],
        )
    return parsed


def _validate(schema: type, raw: dict[str, Any], *, source: str) -> Any:
    from pydantic import ValidationError

    try:
        return schema(**raw)
    except ValidationError as exc:
        unknown = [
            ".".join(str(part) for part in error["loc"])
            for error in exc.errors()
            if error["type"] == "extra_forbidden"
        ]
        if unknown and source == "query":
            raise AppError(ErrorCode.QUERY_UNKNOWN_PARAM, details={"unknown": unknown}) from exc
        raise AppError(ErrorCode.VALIDATION_FAILED, field_errors=field_errors_from_pydantic(exc)) from exc


# ── @paginated ─────────────────────────────────────────────────────────────


def paginated(mode: PaginationMode, *, default_limit: int, max_limit: int) -> Callable[[F], F]:
    """페이지네이션 파라미터 처리. 라우트는 `page`(또는 `cursor`) 인자를 받는다."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            params = current_request().query_params or {}
            limit = clamp_limit(params.get("limit"), default=default_limit, maximum=max_limit)
            if mode == CURSOR:
                raw_cursor = params.get("cursor")
                kwargs["pagination"] = CursorParams(
                    limit=limit, cursor=Cursor.decode(raw_cursor) if raw_cursor else None
                )
            else:
                kwargs["pagination"] = PageParams(limit=limit, page=parse_page(params.get("page")))
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).paginated = mode
        return wrapper  # type: ignore[return-value]

    return decorator


# ── @etag ──────────────────────────────────────────────────────────────────


def etag(*, cache_control: str | None = None) -> Callable[[F], F]:
    """조건부 요청 처리.

    라우트가 `Result.etag`를 채우면, 요청의 `If-None-Match`와 같을 때 `304`로 끊는다.
    본문 전송을 아끼는 것이 목적이며(API 문서 §2.9), 발행 즉시 반영은 그대로 유지된다.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            result = func(**kwargs)
            if isinstance(result, Result) and result.etag:
                incoming = current_request().headers.get("if-none-match")
                if incoming and _etag_matches(incoming, result.etag):
                    raise NotModified(result.etag, cache_control or result.cache_control)
                if cache_control and not result.cache_control:
                    result = Result(
                        data=result.data,
                        status=result.status,
                        pagination=result.pagination,
                        cache_control=cache_control,
                        etag=result.etag,
                        headers=result.headers,
                    )
            return result

        _carry_meta(func, wrapper)
        meta_of(wrapper).etag_enabled = True
        return wrapper  # type: ignore[return-value]

    return decorator


def _etag_matches(header_value: str, current: str) -> bool:
    candidates = {item.strip().removeprefix("W/").strip('"') for item in header_value.split(",")}
    return current.strip('"') in candidates


# ── @throttled ─────────────────────────────────────────────────────────────


def throttled(
    scope: str,
    *,
    key: Callable[[dict[str, Any]], str] | None = None,
    count_attempts: bool = False,
) -> Callable[[F], F]:
    """시도 제한. 초과 시 `Retry-After`와 함께 429를 던진다 (API 문서 §2.10).

    `count_attempts=True`면 **검사와 누적을 함께** 한다. 시간창 방식(가입·재설정·업로드
    자격)은 성공·실패를 가리지 않고 시도 자체를 세기 때문이다. 라우트가 누적을 따로
    호출하지 않게 하는 것이 목적이다 — 관심사를 데코레이터가 흡수한다(문서 §7).

    `login`처럼 **실패만** 세는 스코프는 여기서 검사만 하고, 누적은 판정을 아는
    서비스가 한다.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            context = ctx_module.current()
            identifier = key(kwargs) if key else (str(context.actor_id) if context.actor_id else "anon")
            _guard_throttle(scope, _deps.check_throttle(context.db, scope, identifier))
            if count_attempts:
                _guard_throttle(scope, _deps.record_attempt(scope, identifier))
            return func(**kwargs)

        _carry_meta(func, wrapper)
        meta_of(wrapper).throttle_scope = scope
        return wrapper  # type: ignore[return-value]

    return decorator


def _guard_throttle(scope: str, retry_after: int) -> None:
    if retry_after <= 0:
        return
    # 로그인만 전용 코드를 쓴다. 나머지는 일반 제한이다(API 문서 §5.1·§5.2).
    code = ErrorCode.AUTH_TOO_MANY_ATTEMPTS if scope == "login" else ErrorCode.RATE_LIMITED
    raise AppError(code, details={"retry_after_seconds": retry_after})


# ── @audited ───────────────────────────────────────────────────────────────


def audited(action: str) -> Callable[[F], F]:
    """성공 시 감사 로그를 자동 기록한다. 관리자 변경 조작은 전건 남는다(백엔드 문서 §13)."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            context = ctx_module.current()
            result = func(**kwargs)
            status = result.status if isinstance(result, Result) else 200
            if status < 400:
                _deps.record_audit(context.db, action, context)
            return result

        _carry_meta(func, wrapper)
        meta_of(wrapper).audited_action = action
        return wrapper  # type: ignore[return-value]

    return decorator


def view_parameters(func: Callable[..., Any]) -> set[str]:
    """계약 테스트가 데코레이터 주입 인자와 뷰 시그니처의 일치를 확인할 때 쓴다."""
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return set(inspect.signature(func).parameters)

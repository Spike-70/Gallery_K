"""오류 코드 카탈로그와 예외 (API 문서 §5, 백엔드 문서 §8.2).

**카탈로그는 레지스트리 하나다.** 카탈로그에 없는 코드로 예외를 발생시킬 수 없으며
(`AppError`가 생성 시점에 거부한다), 계약 테스트가 라우트에서 나오는 코드가 전부
여기 있는지 확인한다.

`code`는 전역 유일하고, 한 번 배포된 값은 의미를 바꾸지 않는다. 새 상황은 새 코드다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    code: str
    status: int
    message: str
    retryable: bool
    #: 이 코드가 `details`에 담을 수 있는 키. 문서 §5의 details 열이다.
    detail_keys: tuple[str, ...] = ()


class ErrorCode:
    """코드 상수. 문자열 리터럴을 코드 곳곳에 흩지 않는다."""

    # §5.1 공통
    VALIDATION_FAILED: Final = "VALIDATION_FAILED"
    QUERY_INVALID_SORT: Final = "QUERY_INVALID_SORT"
    QUERY_UNKNOWN_PARAM: Final = "QUERY_UNKNOWN_PARAM"
    PAGINATION_INVALID_CURSOR: Final = "PAGINATION_INVALID_CURSOR"
    NOT_FOUND: Final = "NOT_FOUND"
    CONFLICT_VERSION: Final = "CONFLICT_VERSION"
    RATE_LIMITED: Final = "RATE_LIMITED"
    CSRF_HEADER_MISSING: Final = "CSRF_HEADER_MISSING"
    MAINTENANCE_MODE: Final = "MAINTENANCE_MODE"
    SYSTEM_INTERNAL: Final = "SYSTEM_INTERNAL"
    SYSTEM_DEPENDENCY_UNAVAILABLE: Final = "SYSTEM_DEPENDENCY_UNAVAILABLE"

    # §5.2 인증·계정
    AUTH_REQUIRED: Final = "AUTH_REQUIRED"
    AUTH_INVALID_CREDENTIALS: Final = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOO_MANY_ATTEMPTS: Final = "AUTH_TOO_MANY_ATTEMPTS"
    AUTH_SESSION_EXPIRED: Final = "AUTH_SESSION_EXPIRED"
    AUTH_SESSION_REVOKED: Final = "AUTH_SESSION_REVOKED"
    AUTH_FORBIDDEN: Final = "AUTH_FORBIDDEN"
    SIGNUP_CLOSED: Final = "SIGNUP_CLOSED"
    SIGNUP_PHONE_TAKEN: Final = "SIGNUP_PHONE_TAKEN"
    PASSWORD_POLICY_VIOLATION: Final = "PASSWORD_POLICY_VIOLATION"
    PASSWORD_CURRENT_MISMATCH: Final = "PASSWORD_CURRENT_MISMATCH"
    RESET_CODE_INVALID: Final = "RESET_CODE_INVALID"
    RESET_CODE_EXPIRED: Final = "RESET_CODE_EXPIRED"

    # §5.3 전시·그림
    EXHIBITION_NOT_FOUND: Final = "EXHIBITION_NOT_FOUND"
    EXHIBITION_NOT_OPENED: Final = "EXHIBITION_NOT_OPENED"
    EXHIBITION_BACKFILL_FORBIDDEN: Final = "EXHIBITION_BACKFILL_FORBIDDEN"
    EXHIBITION_ALREADY_HIDDEN: Final = "EXHIBITION_ALREADY_HIDDEN"
    EXHIBITION_NOT_PUBLISHED: Final = "EXHIBITION_NOT_PUBLISHED"
    ARTWORK_NOT_FOUND: Final = "ARTWORK_NOT_FOUND"
    ARTWORK_SLOT_OCCUPIED: Final = "ARTWORK_SLOT_OCCUPIED"
    ARTWORK_IMAGE_NOT_READY: Final = "ARTWORK_IMAGE_NOT_READY"
    DRAFT_TARGET_OCCUPIED: Final = "DRAFT_TARGET_OCCUPIED"
    DRAFT_NOT_FOUND: Final = "DRAFT_NOT_FOUND"
    UPLOAD_FILE_TOO_LARGE: Final = "UPLOAD_FILE_TOO_LARGE"
    UPLOAD_MIME_NOT_ALLOWED: Final = "UPLOAD_MIME_NOT_ALLOWED"
    UPLOAD_EXPIRED: Final = "UPLOAD_EXPIRED"

    # §5.4 회원 관리·설정
    MEMBER_NOT_FOUND: Final = "MEMBER_NOT_FOUND"
    MEMBER_CURATOR_IMMUTABLE: Final = "MEMBER_CURATOR_IMMUTABLE"
    NOTICE_PERIOD_OVERLAP: Final = "NOTICE_PERIOD_OVERLAP"
    NOTICE_PERIOD_INVALID: Final = "NOTICE_PERIOD_INVALID"
    SETTING_IMMUTABLE: Final = "SETTING_IMMUTABLE"
    SETTING_UNKNOWN_KEY: Final = "SETTING_UNKNOWN_KEY"
    PUSH_SUBSCRIPTION_INVALID: Final = "PUSH_SUBSCRIPTION_INVALID"


def _spec(code: str, status: int, message: str, retryable: bool, *details: str) -> ErrorSpec:
    return ErrorSpec(code=code, status=status, message=message, retryable=retryable, detail_keys=details)


#: 오류 코드 카탈로그. API 문서 §5의 표를 그대로 옮긴 것이며 이 사전이 유일한 원천이다.
CATALOG: Final[dict[str, ErrorSpec]] = {
    spec.code: spec
    for spec in (
        # §5.1
        _spec(ErrorCode.VALIDATION_FAILED, 422, "입력한 내용을 다시 확인해 주세요.", False),
        _spec(ErrorCode.QUERY_INVALID_SORT, 400, "잘못된 정렬 조건입니다.", False, "allowed"),
        _spec(ErrorCode.QUERY_UNKNOWN_PARAM, 400, "지원하지 않는 검색 조건입니다.", False, "unknown"),
        _spec(ErrorCode.PAGINATION_INVALID_CURSOR, 400, "목록을 다시 불러와 주세요.", False),
        _spec(ErrorCode.NOT_FOUND, 404, "요청하신 내용을 찾을 수 없습니다.", False, "resource"),
        _spec(
            ErrorCode.CONFLICT_VERSION,
            409,
            "다른 곳에서 먼저 수정되었습니다. 새로고침 후 다시 시도해 주세요.",
            False,
            "current_version",
        ),
        _spec(ErrorCode.RATE_LIMITED, 429, "잠시 후 다시 시도해 주세요.", True, "retry_after_seconds"),
        _spec(
            ErrorCode.CSRF_HEADER_MISSING,
            403,
            "요청을 처리할 수 없습니다. 새로고침 후 다시 시도해 주세요.",
            False,
        ),
        _spec(ErrorCode.MAINTENANCE_MODE, 503, "잠시 점검 중입니다.", True, "until"),
        _spec(ErrorCode.SYSTEM_INTERNAL, 500, "문제가 생겼습니다. 잠시 후 다시 시도해 주세요.", True),
        _spec(
            ErrorCode.SYSTEM_DEPENDENCY_UNAVAILABLE,
            503,
            "일시적으로 연결이 원활하지 않습니다.",
            True,
            "dependency",
        ),
        # §5.2
        _spec(ErrorCode.AUTH_REQUIRED, 401, "로그인이 필요합니다.", False),
        _spec(ErrorCode.AUTH_INVALID_CREDENTIALS, 401, "전화번호 또는 비밀번호가 맞지 않습니다.", False),
        _spec(
            ErrorCode.AUTH_TOO_MANY_ATTEMPTS,
            429,
            "로그인 시도가 많았습니다. 10분 뒤에 다시 시도해 주세요.",
            True,
            "retry_after_seconds",
        ),
        _spec(ErrorCode.AUTH_SESSION_EXPIRED, 401, "로그인이 만료되었습니다. 다시 입장해 주세요.", False),
        _spec(ErrorCode.AUTH_SESSION_REVOKED, 401, "로그인이 만료되었습니다. 다시 입장해 주세요.", False),
        _spec(ErrorCode.AUTH_FORBIDDEN, 403, "접근 권한이 없습니다.", False),
        _spec(ErrorCode.SIGNUP_CLOSED, 403, "지금은 새로운 회원을 받고 있지 않습니다.", False),
        _spec(ErrorCode.SIGNUP_PHONE_TAKEN, 409, "이미 가입된 번호입니다.", False),
        _spec(
            ErrorCode.PASSWORD_POLICY_VIOLATION,
            422,
            "비밀번호는 8자 이상이어야 합니다.",
            False,
            "min_length",
        ),
        _spec(ErrorCode.PASSWORD_CURRENT_MISMATCH, 401, "현재 비밀번호가 맞지 않습니다.", False),
        _spec(ErrorCode.RESET_CODE_INVALID, 422, "인증번호가 맞지 않습니다.", False, "attempts_left"),
        _spec(ErrorCode.RESET_CODE_EXPIRED, 422, "인증번호가 만료되었습니다. 다시 받아 주세요.", False),
        # §5.3
        _spec(ErrorCode.EXHIBITION_NOT_FOUND, 404, "전시를 찾을 수 없습니다.", False, "date"),
        _spec(ErrorCode.EXHIBITION_NOT_OPENED, 404, "첫 전시를 준비하고 있습니다.", False),
        _spec(
            ErrorCode.EXHIBITION_BACKFILL_FORBIDDEN,
            409,
            "지난 날짜에는 새 전시를 걸 수 없습니다.",
            False,
            "date",
            "today",
        ),
        _spec(ErrorCode.EXHIBITION_ALREADY_HIDDEN, 409, "이미 숨겨진 전시입니다.", False),
        _spec(ErrorCode.EXHIBITION_NOT_PUBLISHED, 409, "아직 발행되지 않은 전시입니다.", False),
        _spec(ErrorCode.ARTWORK_NOT_FOUND, 404, "그림을 찾을 수 없습니다.", False),
        _spec(ErrorCode.ARTWORK_SLOT_OCCUPIED, 409, "이미 그림이 있는 자리입니다.", False, "position"),
        _spec(
            ErrorCode.ARTWORK_IMAGE_NOT_READY,
            409,
            "이미지 준비가 끝나지 않았습니다.",
            True,
            "image_status",
        ),
        _spec(
            ErrorCode.DRAFT_TARGET_OCCUPIED,
            409,
            "오늘 날짜에 이미 작업 중인 전시가 있습니다.",
            False,
            "target_date",
        ),
        _spec(ErrorCode.DRAFT_NOT_FOUND, 404, "이어 쓸 작업물이 없습니다.", False),
        _spec(
            ErrorCode.UPLOAD_FILE_TOO_LARGE,
            413,
            "이미지는 20MB까지 올릴 수 있습니다.",
            False,
            "max_bytes",
        ),
        _spec(
            ErrorCode.UPLOAD_MIME_NOT_ALLOWED,
            422,
            "JPG, PNG, WebP 파일만 올릴 수 있습니다.",
            False,
            "allowed",
        ),
        _spec(ErrorCode.UPLOAD_EXPIRED, 409, "업로드 시간이 지났습니다. 다시 시도해 주세요.", True),
        # §5.4
        _spec(ErrorCode.MEMBER_NOT_FOUND, 404, "회원을 찾을 수 없습니다.", False),
        _spec(ErrorCode.MEMBER_CURATOR_IMMUTABLE, 403, "관리자 계정은 변경할 수 없습니다.", False),
        _spec(
            ErrorCode.NOTICE_PERIOD_OVERLAP,
            409,
            "이미 같은 기간에 공지가 있습니다.",
            False,
            "conflict_notice_id",
        ),
        _spec(ErrorCode.NOTICE_PERIOD_INVALID, 422, "종료일은 시작일보다 빠를 수 없습니다.", False),
        _spec(ErrorCode.SETTING_IMMUTABLE, 403, "변경할 수 없는 설정입니다.", False, "key"),
        _spec(ErrorCode.SETTING_UNKNOWN_KEY, 400, "알 수 없는 설정입니다.", False, "key"),
        _spec(
            ErrorCode.PUSH_SUBSCRIPTION_INVALID,
            422,
            "알림 설정에 실패했습니다. 다시 시도해 주세요.",
            False,
        ),
    )
}


class FieldErrorCode:
    """`field_errors[].code` (API 문서 §2.5)."""

    REQUIRED: Final = "REQUIRED"
    TOO_LONG: Final = "TOO_LONG"
    TOO_SHORT: Final = "TOO_SHORT"
    INVALID_FORMAT: Final = "INVALID_FORMAT"
    OUT_OF_RANGE: Final = "OUT_OF_RANGE"
    NOT_ALLOWED: Final = "NOT_ALLOWED"


FIELD_ERROR_CODES: Final = frozenset(
    {
        FieldErrorCode.REQUIRED,
        FieldErrorCode.TOO_LONG,
        FieldErrorCode.TOO_SHORT,
        FieldErrorCode.INVALID_FORMAT,
        FieldErrorCode.OUT_OF_RANGE,
        FieldErrorCode.NOT_ALLOWED,
    }
)


@dataclass(frozen=True, slots=True)
class FieldError:
    """필드 옆에 그대로 출력되는 오류. 폼 라이브러리에 1:1로 매핑된다."""

    field: str
    code: str
    message: str
    limit: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "limit": self.limit,
        }


class AppError(Exception):
    """모든 도메인 오류의 단일 기반.

    코드가 카탈로그에 없으면 **생성 자체가 실패**한다. 문서에 없는 코드가 응답으로
    나가는 경로를 구조적으로 없앤다.
    """

    __slots__ = ("_message", "code", "details", "doc_hint", "field_errors", "spec")

    def __init__(
        self,
        code: str,
        *,
        details: dict[str, Any] | None = None,
        field_errors: list[FieldError] | None = None,
        message: str | None = None,
        doc_hint: str | None = None,
    ) -> None:
        spec = CATALOG.get(code)
        if spec is None:
            raise LookupError(f"카탈로그에 없는 오류 코드입니다: {code} (API 문서 §5)")
        self.code = code
        self.spec = spec
        self.details = details or None
        self.field_errors = field_errors or None
        self._message = message
        self.doc_hint = doc_hint
        super().__init__(f"{code}: {self.message}")

    @property
    def message(self) -> str:
        """최종 사용자에게 그대로 보여줄 수 있는 한국어 문장."""
        return self._message or self.spec.message

    @property
    def status(self) -> int:
        return self.spec.status

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    def to_dict(self, *, include_doc_hint: bool) -> dict[str, Any]:
        """`error` 봉투. 키를 생략하지 않는다 — 프런트 타입이 옵셔널 지옥이 되는 것을 막는다."""
        return {
            "code": self.code,
            "message": self.message,
            "field_errors": [item.to_dict() for item in self.field_errors] if self.field_errors else None,
            "details": self.details,
            "retryable": self.retryable,
            # 프로덕션에서는 항상 null이다 (API 문서 §2.5)
            "doc_hint": self.doc_hint if include_doc_hint else None,
        }


@dataclass(frozen=True, slots=True)
class ConstraintMapping:
    code: str
    details: dict[str, Any] = field(default_factory=dict)


#: 제약 위반 → 오류 코드. 사전 조회로도 경쟁 조건은 남으므로 이 매핑이 필수다(백엔드 문서 §8.2).
CONSTRAINT_ERROR_MAP: Final[dict[str, ConstraintMapping]] = {
    "uq_app_user_phone": ConstraintMapping(ErrorCode.SIGNUP_PHONE_TAKEN),
    "uq_exhibition_date": ConstraintMapping(ErrorCode.CONFLICT_VERSION),
    "uq_artwork_exhibition_position": ConstraintMapping(ErrorCode.ARTWORK_SLOT_OCCUPIED),
    "ex_notice_active_period": ConstraintMapping(ErrorCode.NOTICE_PERIOD_OVERLAP),
    "ck_notice_period_order": ConstraintMapping(ErrorCode.NOTICE_PERIOD_INVALID),
    "ck_artwork_position_range": ConstraintMapping(
        ErrorCode.VALIDATION_FAILED,
    ),
}


def error_for_constraint(constraint_name: str | None) -> AppError | None:
    """제약명으로 사용자 대면 오류를 고른다. 모르는 제약이면 None — 내부 오류로 떨어진다."""
    if not constraint_name:
        return None
    mapping = CONSTRAINT_ERROR_MAP.get(constraint_name)
    if mapping is None:
        return None
    return AppError(mapping.code, details=dict(mapping.details) or None)


def translate_exception(exc: BaseException) -> AppError:
    """원천 예외를 사용자 대면 오류로 바꾸는 **유일한 지점** (백엔드 문서 §8.2).

    변환 규칙
      * 이미 `AppError`면 그대로
      * 스키마 검증 오류 → 필드 오류
      * 제약 위반 → 제약명 기반 코드 매핑 (사전 조회로도 경쟁 조건은 남는다)
      * 버전 충돌 → 충돌 코드
      * 연결 오류 → 의존성 오류
      * 그 외 → 내부 오류 (상세는 로그에만 남는다)

    무거운 라이브러리를 모듈 로드 시점에 끌어오지 않으려고 import를 함수 안에 둔다
    (백엔드 문서 §14 콜드 스타트).
    """
    if isinstance(exc, AppError):
        return exc

    from pydantic import ValidationError as PydanticValidationError

    if isinstance(exc, PydanticValidationError):
        return AppError(ErrorCode.VALIDATION_FAILED, field_errors=field_errors_from_pydantic(exc))

    from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
    from sqlalchemy.orm.exc import StaleDataError

    if isinstance(exc, IntegrityError):
        mapped = error_for_constraint(constraint_name_of(exc))
        if mapped is not None:
            return mapped
        return AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint=f"제약 위반: {constraint_name_of(exc)}")

    if isinstance(exc, StaleDataError):
        return AppError(ErrorCode.CONFLICT_VERSION)

    if isinstance(exc, OperationalError | DBAPIError):
        return AppError(ErrorCode.SYSTEM_DEPENDENCY_UNAVAILABLE, details={"dependency": "database"})

    return AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint=f"{type(exc).__name__}: {exc}")


def constraint_name_of(exc: BaseException) -> str | None:
    """psycopg3의 진단 정보에서 제약명을 꺼낸다. 문자열 파싱에 의존하지 않는다."""
    original = getattr(exc, "orig", None)
    diagnostic = getattr(original, "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    if name:
        return str(name)
    # 진단 정보가 없는 드라이버를 위한 최후 수단
    text = str(exc)
    for constraint in CONSTRAINT_ERROR_MAP:
        if constraint in text:
            return constraint
    return None


def field_errors_from_pydantic(exc: Any) -> list[FieldError]:
    """pydantic 오류를 `field_errors` 규약으로 옮긴다 (API 문서 §2.5).

    경로 표기는 요청 바디 기준이며 중첩은 점, 배열은 인덱스다 (`artworks.3.description`).
    """
    results: list[FieldError] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        results.append(
            FieldError(
                field=location,
                code=_FIELD_CODE_BY_PYDANTIC_TYPE.get(error["type"], FieldErrorCode.INVALID_FORMAT),
                message=str(error.get("ctx", {}).get("message") or _field_message(error)),
                limit=_field_limit(error),
            )
        )
    return results


_FIELD_CODE_BY_PYDANTIC_TYPE: Final[dict[str, str]] = {
    "missing": FieldErrorCode.REQUIRED,
    "string_too_long": FieldErrorCode.TOO_LONG,
    "string_too_short": FieldErrorCode.TOO_SHORT,
    "too_long": FieldErrorCode.TOO_LONG,
    "too_short": FieldErrorCode.TOO_SHORT,
    "string_pattern_mismatch": FieldErrorCode.INVALID_FORMAT,
    "value_error": FieldErrorCode.INVALID_FORMAT,
    "greater_than": FieldErrorCode.OUT_OF_RANGE,
    "greater_than_equal": FieldErrorCode.OUT_OF_RANGE,
    "less_than": FieldErrorCode.OUT_OF_RANGE,
    "less_than_equal": FieldErrorCode.OUT_OF_RANGE,
    "enum": FieldErrorCode.NOT_ALLOWED,
    "literal_error": FieldErrorCode.NOT_ALLOWED,
    "bool_parsing": FieldErrorCode.INVALID_FORMAT,
    "int_parsing": FieldErrorCode.INVALID_FORMAT,
    "date_from_datetime_parsing": FieldErrorCode.INVALID_FORMAT,
    "extra_forbidden": FieldErrorCode.NOT_ALLOWED,
}

_FIELD_MESSAGE_BY_CODE: Final[dict[str, str]] = {
    FieldErrorCode.REQUIRED: "필수 입력입니다.",
    FieldErrorCode.TOO_LONG: "너무 깁니다.",
    FieldErrorCode.TOO_SHORT: "너무 짧습니다.",
    FieldErrorCode.INVALID_FORMAT: "형식이 올바르지 않습니다.",
    FieldErrorCode.OUT_OF_RANGE: "허용 범위를 벗어났습니다.",
    FieldErrorCode.NOT_ALLOWED: "허용되지 않는 값입니다.",
}


def _field_message(error: dict[str, Any]) -> str:
    code = _FIELD_CODE_BY_PYDANTIC_TYPE.get(error["type"], FieldErrorCode.INVALID_FORMAT)
    limit = _field_limit(error)
    if code == FieldErrorCode.TOO_LONG and limit is not None:
        return f"{int(limit)}자까지 쓸 수 있습니다."
    return _FIELD_MESSAGE_BY_CODE[code]


def _field_limit(error: dict[str, Any]) -> float | None:
    ctx = error.get("ctx") or {}
    for key in ("max_length", "min_length", "le", "ge", "lt", "gt", "max_digits"):
        if key in ctx:
            try:
                return float(ctx[key])
            except (TypeError, ValueError):
                return None
    return None

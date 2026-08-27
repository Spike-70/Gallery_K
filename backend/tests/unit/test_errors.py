"""오류 카탈로그 — 레지스트리 하나 (API 문서 §5, 백엔드 문서 §8.2)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from chalicelib.core.errors import (
    CATALOG,
    FIELD_ERROR_CODES,
    AppError,
    ErrorCode,
    translate_exception,
)


def test_catalog_covers_every_documented_code() -> None:
    """API 문서 §5의 50개 코드. 값이 늘거나 줄면 문서와 함께 바뀌어야 한다."""
    assert len(CATALOG) == 50
    declared = {
        value
        for name, value in vars(ErrorCode).items()
        if not name.startswith("_") and isinstance(value, str)
    }
    assert declared == set(CATALOG)


def test_every_spec_is_self_consistent() -> None:
    for code, spec in CATALOG.items():
        assert spec.code == code
        assert 400 <= spec.status <= 599
        assert spec.message.endswith(".")
        # 사용자 문구에 기술 용어·식별자를 담지 않는다 (API 문서 §2.5)
        assert "None" not in spec.message


def test_unknown_code_cannot_be_raised() -> None:
    with pytest.raises(LookupError):
        AppError("NOT_IN_CATALOG")


def test_error_body_keeps_every_key() -> None:
    """키를 생략하지 않는다 — 프런트 타입이 옵셔널 지옥이 되는 것을 막는다."""
    payload = AppError(ErrorCode.NOT_FOUND).to_dict(include_doc_hint=False)
    assert set(payload) == {"code", "message", "field_errors", "details", "retryable", "doc_hint"}


def test_doc_hint_is_hidden_in_production_mode() -> None:
    error = AppError(ErrorCode.SYSTEM_INTERNAL, doc_hint="stack detail")
    assert error.to_dict(include_doc_hint=False)["doc_hint"] is None
    assert error.to_dict(include_doc_hint=True)["doc_hint"] == "stack detail"


class _Payload(BaseModel):
    title: str = Field(max_length=5)
    position: int = Field(ge=1, le=12)


def test_schema_error_becomes_field_errors() -> None:
    with pytest.raises(ValidationError) as caught:
        _Payload(title="너무나도 긴 제목입니다", position=99)
    error = translate_exception(caught.value)
    assert error.code == ErrorCode.VALIDATION_FAILED
    assert error.status == 422
    assert error.field_errors is not None
    codes = {item.code for item in error.field_errors}
    assert codes <= FIELD_ERROR_CODES
    by_field = {item.field: item for item in error.field_errors}
    assert by_field["title"].code == "TOO_LONG"
    assert by_field["title"].limit == 5
    assert by_field["position"].code == "OUT_OF_RANGE"


def test_unknown_exception_becomes_internal_with_hint_only() -> None:
    error = translate_exception(RuntimeError("데이터베이스가 폭발했습니다"))
    assert error.code == ErrorCode.SYSTEM_INTERNAL
    assert error.retryable is True
    # 상세는 로그에만 남는다. 사용자 문구는 카탈로그 기본값이다.
    assert error.message == CATALOG[ErrorCode.SYSTEM_INTERNAL].message

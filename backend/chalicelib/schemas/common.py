"""응답 봉투와 공용 리소스 스키마 (API 문서 §2.2·§3).

여기 있는 모델은 **계약의 문서이자 검사기**다. 요청 스키마는 `@body`/`@query`가 런타임에
쓰고, 응답 스키마는 계약 테스트가 전 라우트의 응답을 검증하는 데 쓴다(백엔드 문서 §12
"전 응답이 봉투 스키마를 만족한다").

서비스는 이 모듈을 import 하지 않는다(BA-5). 서비스가 만드는 dict가 이 모양을 만족하는지는
계약 테스트가 확인한다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

#: 요청 스키마의 공통 설정 — 모르는 필드는 거부한다(오타로 조건이 조용히 풀리지 않게).
STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PaginationMeta(BaseModel):
    mode: Literal["cursor", "page"]
    limit: int
    count: int
    has_more: bool
    next_cursor: str | None
    page: int | None
    total_count: int | None
    total_pages: int | None


class DeprecationMeta(BaseModel):
    sunset_on: str
    replacement: str


class ResponseMeta(BaseModel):
    request_id: str = Field(min_length=26, max_length=26)
    server_time: str
    server_date: str
    api_version: Literal["v1"]
    pagination: PaginationMeta | None
    deprecation: DeprecationMeta | None


class FieldErrorOut(BaseModel):
    field: str
    code: Literal["REQUIRED", "TOO_LONG", "TOO_SHORT", "INVALID_FORMAT", "OUT_OF_RANGE", "NOT_ALLOWED"]
    message: str
    limit: float | None


class ErrorOut(BaseModel):
    code: str
    message: str
    field_errors: list[FieldErrorOut] | None
    details: dict[str, Any] | None
    retryable: bool
    doc_hint: str | None


class Envelope(BaseModel):
    """성공·실패의 키 집합이 완전히 같다. 프런트는 `success` 하나만 보고 분기한다."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    data: Any
    meta: ResponseMeta
    error: ErrorOut | None


class ImageSetOut(BaseModel):
    """§3.1. URL은 응답 시점에 발급되는 presigned GET URL이며 만료가 있다."""

    thumb_url: str
    display_url: str
    origin_url: str | None
    lqip: str | None
    width: int | None
    height: int | None
    aspect_ratio: float | None


class NoticeItemOut(BaseModel):
    """§3.7."""

    id: str
    starts_on: str
    ends_on: str
    body: str
    is_active: bool

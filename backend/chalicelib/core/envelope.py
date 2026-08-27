"""표준 응답 봉투 (API 문서 §2.2·§2.3).

성공·실패의 **키 집합이 완전히 동일**하다. 프런트엔드는 `success` 하나만 보고 분기하며
타입 정의도 판별 유니온 하나로 끝난다.

이 모듈은 프레임워크를 모른다. Chalice `Response` 조립은 `core/middleware.py`가 한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chalicelib.config.constants import API_VERSION
from chalicelib.core.context import RequestContext
from chalicelib.core.errors import AppError
from chalicelib.core.timeutil import format_date, format_rfc3339


@dataclass(frozen=True, slots=True)
class Deprecation:
    sunset_on: str
    replacement: str

    def to_dict(self) -> dict[str, Any]:
        return {"sunset_on": self.sunset_on, "replacement": self.replacement}


def build_meta(
    context: RequestContext,
    *,
    pagination: dict[str, Any] | None = None,
    deprecation: Deprecation | None = None,
) -> dict[str, Any]:
    """`server_date`는 **KST 오늘**이다. 클라이언트는 단말 시계로 날짜를 계산하지 않는다."""
    return {
        "request_id": context.request_id,
        "server_time": format_rfc3339(context.now),
        "server_date": format_date(context.today),
        "api_version": API_VERSION,
        "pagination": pagination,
        "deprecation": deprecation.to_dict() if deprecation else None,
    }


def success_body(
    data: Any,
    context: RequestContext,
    *,
    pagination: dict[str, Any] | None = None,
    deprecation: Deprecation | None = None,
) -> dict[str, Any]:
    """액션형 API도 최소 `{}`를 반환한다 — `data`가 없는 성공 응답은 없다."""
    return {
        "success": True,
        "data": {} if data is None else data,
        "meta": build_meta(context, pagination=pagination, deprecation=deprecation),
        "error": None,
    }


def error_body(error: AppError, context: RequestContext, *, include_doc_hint: bool) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "meta": build_meta(context),
        "error": error.to_dict(include_doc_hint=include_doc_hint),
    }


ENVELOPE_KEYS: frozenset[str] = frozenset({"success", "data", "meta", "error"})
META_KEYS: frozenset[str] = frozenset(
    {"request_id", "server_time", "server_date", "api_version", "pagination", "deprecation"}
)


@dataclass(frozen=True, slots=True)
class Result:
    """라우트가 돌려주는 값.

    라우트는 봉투를 만들지 않는다 — `data`와, 그 응답에만 해당하는 부가 정보만 준다.
    봉투 조립은 경계 한 곳에서 이루어진다(백엔드 문서 §6 `response_finalize`).
    """

    data: Any = None
    status: int = 200
    pagination: dict[str, Any] | None = None
    cache_control: str | None = None
    etag: str | None = None
    headers: dict[str, str] | None = None


# 오류가 아니라 조건부 응답 신호다 — 이름에 Error를 붙이지 않는다.
class NotModified(Exception):
    """`304`. 봉투 규약의 유일한 예외이며 본문이 비어 있다 (API 문서 §2.9)."""

    def __init__(self, etag: str, cache_control: str | None = None) -> None:
        self.etag = etag
        self.cache_control = cache_control
        super().__init__("not modified")

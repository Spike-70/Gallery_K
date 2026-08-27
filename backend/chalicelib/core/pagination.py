"""페이지네이션 규약 (API 문서 §2.4).

두 가지 모드를 두되 **응답 구조는 동일**하게 유지한다. 항목이 30개뿐인 목록도 같은
`meta.pagination`을 반환한다 — 프런트의 목록 훅이 하나로 유지된다(AP-5).

커서는 `base64url(json({"k": 정렬키, "id": 타이브레이커}))`이며 **서버 내부 규약**이다.
클라이언트는 해석하지 않는다.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Final, Literal

from chalicelib.config.constants import PAGINATION_MAX_LIMIT
from chalicelib.core.errors import AppError, ErrorCode

PaginationMode = Literal["cursor", "page"]

CURSOR: Final[PaginationMode] = "cursor"
PAGE: Final[PaginationMode] = "page"


@dataclass(frozen=True, slots=True)
class Cursor:
    """정렬키와 타이브레이커. 삽입으로 인한 페이지 밀림이 없다."""

    key: Any
    id: str

    def encode(self) -> str:
        raw = json.dumps({"k": self.key, "id": self.id}, separators=(",", ":"), default=str)
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    @classmethod
    def decode(cls, value: str) -> Cursor:
        try:
            padded = value + "=" * (-len(value) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
            return cls(key=payload["k"], id=str(payload["id"]))
        # 어떤 형태로 깨진 커서든 같은 응답을 준다 — 내부 규약을 노출하지 않는다.
        except Exception as exc:
            raise AppError(ErrorCode.PAGINATION_INVALID_CURSOR) from exc


@dataclass(frozen=True, slots=True)
class CursorParams:
    limit: int
    cursor: Cursor | None


@dataclass(frozen=True, slots=True)
class PageParams:
    limit: int
    page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def clamp_limit(raw: Any, *, default: int, maximum: int = PAGINATION_MAX_LIMIT) -> int:
    """범위를 벗어난 `limit`은 잘라 낸다. 목록 크기는 서버가 정한다."""
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="limit은 정수여야 합니다") from exc
    return max(1, min(value, maximum))


def parse_page(raw: Any) -> int:
    if raw is None or raw == "":
        return 1
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, doc_hint="page는 정수여야 합니다") from exc
    return max(1, value)


def cursor_meta(*, limit: int, count: int, has_more: bool, next_cursor: str | None) -> dict[str, Any]:
    """모드에 관계없이 키 집합이 같다. 유효하지 않은 키는 null로 채운다."""
    return {
        "mode": CURSOR,
        "limit": limit,
        "count": count,
        "has_more": has_more,
        "next_cursor": next_cursor if has_more else None,
        "page": None,
        "total_count": None,
        "total_pages": None,
    }


def page_meta(*, limit: int, count: int, page: int, total_count: int) -> dict[str, Any]:
    total_pages = (total_count + limit - 1) // limit if limit else 0
    return {
        "mode": PAGE,
        "limit": limit,
        "count": count,
        "has_more": page < total_pages,
        "next_cursor": None,
        "page": page,
        "total_count": total_count,
        "total_pages": total_pages,
    }

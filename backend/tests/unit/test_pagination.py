"""페이지네이션 규약 (API 문서 §2.4)."""

from __future__ import annotations

import pytest

from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.pagination import Cursor, clamp_limit, cursor_meta, page_meta, parse_page

_KEYS = {"mode", "limit", "count", "has_more", "next_cursor", "page", "total_count", "total_pages"}


def test_both_modes_share_the_same_key_set() -> None:
    """구조가 같아야 프런트의 목록 훅이 하나로 유지된다 (AP-5)."""
    assert set(cursor_meta(limit=30, count=30, has_more=True, next_cursor="c")) == _KEYS
    assert set(page_meta(limit=30, count=12, page=1, total_count=42)) == _KEYS


def test_cursor_round_trips() -> None:
    cursor = Cursor(key="2026-08-27", id="0199-abc")
    assert Cursor.decode(cursor.encode()) == cursor


def test_broken_cursor_gives_one_answer() -> None:
    for broken in ("!!!", "", "eyJ4Ijoie", "bm90LWpzb24="):
        with pytest.raises(AppError) as caught:
            Cursor.decode(broken)
        assert caught.value.code == ErrorCode.PAGINATION_INVALID_CURSOR


def test_next_cursor_is_null_on_last_page() -> None:
    assert cursor_meta(limit=30, count=4, has_more=False, next_cursor="c")["next_cursor"] is None


def test_page_meta_computes_total_pages() -> None:
    meta = page_meta(limit=30, count=30, page=2, total_count=61)
    assert meta["total_pages"] == 3
    assert meta["has_more"] is True


def test_limit_is_clamped_by_the_server() -> None:
    assert clamp_limit("500", default=30, maximum=30) == 30
    assert clamp_limit(None, default=7, maximum=30) == 7
    assert clamp_limit("0", default=7, maximum=30) == 1
    assert parse_page("0") == 1


def test_non_numeric_pagination_input_is_rejected() -> None:
    with pytest.raises(AppError):
        clamp_limit("삼십", default=30, maximum=30)

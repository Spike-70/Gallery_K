"""계약 테스트 — 라우트 입출력·봉투 구조·오류 코드·권한 (백엔드 문서 §12).

DB 없이 도는 것이 목적이다. 파이프라인(미들웨어 8종 + 데코레이터)이 규약을 지키는지를
보는 것이지 도메인 동작을 보는 것이 아니다.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from chalice.test import Client

from chalicelib.config.constants import CSRF_HEADER_NAME, CSRF_HEADER_VALUE


@pytest.fixture()
def client() -> Iterator[Client]:
    from app import app as chalice_app

    with Client(chalice_app) as test_client:
        yield test_client


@pytest.fixture()
def csrf_headers() -> dict[str, str]:
    return {CSRF_HEADER_NAME: CSRF_HEADER_VALUE}


def assert_envelope(body: Any) -> None:
    """성공·실패의 키 집합이 완전히 같다 (API 문서 §2.2)."""
    from chalicelib.schemas.common import Envelope

    assert set(body) == {"success", "data", "meta", "error"}
    Envelope.model_validate(body)
    if body["success"]:
        assert body["error"] is None
        assert body["data"] is not None
    else:
        assert body["data"] is None
        assert body["error"] is not None

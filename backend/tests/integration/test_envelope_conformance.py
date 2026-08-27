"""메타 테스트 ② — **전 응답이 봉투 스키마를 만족한다** (백엔드 문서 §12).

레지스트리에 등록된 모든 라우트를 실제로 한 번씩 호출하고, 성공이든 실패든 봉투 규약을
지키는지 확인한다. 개별 기능 테스트가 아니라 **새 라우트가 자동으로 검사 대상이 되게
하는 장치**다 — 라우트를 추가하면 다음 실행부터 여기에 포함된다.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.config.constants import MUTATING_METHODS
from chalicelib.core.errors import CATALOG
from chalicelib.core.timeutil import freeze_time
from chalicelib.db import query as q
from chalicelib.schemas.common import Envelope

from .factories import make_exhibition
from .fake_storage import install as install_fake_storage
from .helpers import auth_headers, curator_token, json_body

pytestmark = pytest.mark.integration

TODAY = dt.date(2026, 8, 27)
FROZEN = dt.datetime(2026, 8, 27, 3, 0, tzinfo=dt.UTC)

#: 경로 변수를 채우는 값. 라우트를 추가할 때 새 변수 이름이 생기면 여기에 더한다.
_PLACEHOLDERS = {
    "date": "2026-08-27",
    "position": "1",
    "provider": "kakao",
}

#: **봉투 규약의 예외**(API 문서 §2.2). 브라우저 내비게이션의 종착지라 응답의 본체가
#: `Location` 헤더다. 면제는 여기에 이름을 적어야만 성립하며, 적힌 경로는 아래
#: `test_redirect_routes_are_the_only_envelope_exception`이 **실제로 302인지** 확인한다.
_REDIRECT_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/auth/social/{provider}/start"),
        ("GET", "/auth/social/{provider}/callback"),
    }
)

#: 본문이 필요한 경로의 최소 유효 입력. 없으면 빈 객체를 보낸다.
_BODIES: dict[tuple[str, str], dict[str, Any]] = {
    ("POST", "/auth/signup"): {
        "phone": "01099990000",
        "password": "password123",
        "name": "봉투검사",
        "agreed_terms": True,
    },
    ("POST", "/auth/login"): {"phone": "01099990000", "password": "password123"},
    ("POST", "/auth/password"): {"current_password": "x", "new_password": "password123"},
    ("POST", "/auth/password/reset/request"): {"phone": "01099990000"},
    ("POST", "/auth/password/reset/confirm"): {
        "phone": "01099990000",
        "code": "123456",
        "new_password": "password123",
    },
    ("PATCH", "/me/settings"): {"notify_at": "08:00"},
    ("DELETE", "/me"): {"confirm": True},
    ("POST", "/me/push-subscriptions"): {
        "endpoint": "https://example.com/push/envelope",
        "keys": {"p256dh": "k", "auth": "a"},
    },
    ("PUT", "/admin/exhibitions/{date}"): {"title": "제목", "theme": "테마"},
    ("PUT", "/admin/exhibitions/{date}/artworks/{position}"): {
        "title": "그림",
        "artist": "작가",
        "year_text": "1665년경",
        "description": "설명",
        "collection": None,
        "source_url": None,
    },
    ("POST", "/admin/exhibitions/{date}/artworks/reorder"): {"order": []},
    ("POST", "/admin/exhibitions/{date}/artworks/upload-urls"): {
        "files": [
            {
                "position": 1,
                "filename": "a.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 1000,
            }
        ]
    },
    ("POST", "/admin/artworks/{artwork_id}/image/complete"): {"object_key": "uploads/x/y.jpg"},
    ("POST", "/admin/exhibitions/{date}/hide"): {"reason": None},
    ("POST", "/admin/exhibitions/{date}/carry-draft"): {"confirm": True},
    ("POST", "/admin/members"): {
        "phone": "01088880000",
        "name": "대행",
        "initial_password": "password123",
    },
    ("POST", "/admin/members/{member_id}/block"): {"reason": None},
    ("POST", "/admin/members/{member_id}/reset-password"): {"new_password": "password123"},
    ("PATCH", "/admin/settings"): {"settings": {"signup_open": True}},
    ("POST", "/admin/notices"): {
        "starts_on": "2026-12-01",
        "ends_on": "2026-12-02",
        "body": "휴관",
    },
    ("PATCH", "/admin/notices/{notice_id}"): {"body": "수정"},
    ("GET", "/admin/stats/members"): {},
    # 연결 티켓 쿠키가 없으므로 SOCIAL_LINK_EXPIRED 봉투가 나온다. 그것이 검사 대상이다.
    ("POST", "/auth/social/link"): {"phone": "01099990000", "password": "password123"},
    ("POST", "/auth/social/signup"): {
        "phone": "01066660000",
        "name": "소셜",
        "agreed_terms": True,
    },
}

#: 쿼리 파라미터가 필수인 경로.
_QUERIES: dict[str, str] = {"/admin/stats/members": "?query=검사"}


def _fill(path: str, ids: dict[str, str]) -> str:
    filled = path
    for name, value in {**_PLACEHOLDERS, **ids}.items():
        filled = filled.replace("{" + name + "}", value)
    return filled


def test_every_registered_route_answers_with_the_standard_envelope(
    api_client: Any, write_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_storage(monkeypatch)
    from chalicelib.api.routes._base import REGISTRY
    from chalicelib.db.models import AppUser, Artwork, Notice

    make_exhibition(write_session, TODAY)
    q.insert(
        write_session,
        Notice,
        {
            "starts_on": dt.date(2026, 11, 1),
            "ends_on": dt.date(2026, 11, 2),
            "body": "공지",
            "is_active": True,
        },
    )
    write_session.commit()
    token = curator_token(api_client, write_session)

    member = q.insert(
        write_session,
        AppUser,
        {"phone": "01077770000", "password_hash": "x" * 60, "name": "회원"},
    )
    write_session.commit()
    artwork = q.fetch_one(write_session, Artwork, where={"position": 1})
    notice = q.fetch_one(write_session, Notice)
    assert artwork is not None and notice is not None

    ids = {
        "artwork_id": str(artwork.id),
        "member_id": str(member.id),
        "notice_id": str(notice.id),
        "subscription_id": str(member.id),
        "identity_id": str(member.id),
    }

    checked = 0
    for entry in REGISTRY:
        # 세션을 끊는 경로는 이후 검사를 방해하므로 제외한다. 각자의 테스트가 이미 덮는다.
        if entry.path in {"/auth/logout", "/me"} and entry.method in {"POST", "DELETE"}:
            continue
        if (entry.method, entry.path) in _REDIRECT_ROUTES:
            continue

        url = _fill(entry.path, ids) + _QUERIES.get(entry.path, "")
        body = _BODIES.get((entry.method, entry.path))
        headers = auth_headers(token, csrf=entry.method in MUTATING_METHODS)
        caller = getattr(api_client.http, entry.method.lower())

        response = (
            caller(url, headers=headers, body=json_body(body or {}))
            if entry.method in MUTATING_METHODS
            else caller(url, headers=headers)
        )

        assert response.status_code != 500, f"{entry.method} {url} → 500"
        payload = response.json_body
        assert set(payload) == {"success", "data", "meta", "error"}, f"{entry.method} {url}"
        Envelope.model_validate(payload)

        if payload["success"]:
            assert payload["error"] is None
        else:
            assert payload["data"] is None
            # ③ 발생하는 오류 코드가 카탈로그에 있다.
            assert payload["error"]["code"] in CATALOG, f"{entry.method} {url}"
        checked += 1

    assert checked >= 45, f"검사한 라우트가 너무 적습니다: {checked}"


def test_redirect_routes_are_the_only_envelope_exception(api_client: Any) -> None:
    """면제 목록의 경로가 **실제로 리다이렉트인지** 확인한다.

    면제만 적어 두고 검사하지 않으면 그 목록은 봉투 규약을 우회하는 뒷문이 된다.
    여기서 302와 `Location`을 요구하므로, 면제된 경로도 자기 규약을 지킨다.

    **목적지는 검사하지 않는다.** 제공자 자격이 설정되어 있으면 제공자로, 없으면
    A-1으로 간다 — 개발자의 `.env`에 따라 갈리는 값이다. 이 검사의 요점은 어느
    경우든 JSON 봉투가 아니라 리다이렉트로 끝난다는 것이며, 목적지별 동작은
    `test_social_routes.py`가 자격을 명시적으로 고정해 두고 검증한다.
    """
    from chalicelib.api.routes._base import REGISTRY

    registered = {(entry.method, entry.path) for entry in REGISTRY}
    assert registered >= _REDIRECT_ROUTES, "면제 목록에 없는 라우트가 있습니다"

    for method, path in sorted(_REDIRECT_ROUTES):
        response = getattr(api_client.http, method.lower())(_fill(path, {}))
        assert response.status_code == 302, f"{method} {path} → {response.status_code}"
        assert response.headers.get("Location"), f"{method} {path}: Location 이 없다"
        assert response.body in (b"", ""), f"{method} {path}: 리다이렉트에 본문이 있다"


def test_admin_routes_are_never_cached(api_client: Any, write_session: Session) -> None:
    """오류 응답까지 예외 없이 `no-store`다 — 미들웨어가 경로로 못박는다."""
    from chalicelib.api.routes._base import REGISTRY

    make_exhibition(write_session, TODAY)
    write_session.commit()
    token = curator_token(api_client, write_session)
    ids = {"artwork_id": "00000000-0000-0000-0000-000000000000", "member_id": "not-a-uuid"}

    with freeze_time(FROZEN):
        for entry in REGISTRY:
            if not entry.path.startswith("/admin") or entry.method != "GET":
                continue
            url = _fill(entry.path, ids) + _QUERIES.get(entry.path, "")
            response = api_client.http.get(url, headers=auth_headers(token, csrf=False))
            assert response.headers["Cache-Control"] == "no-store", url


def test_every_response_carries_the_indexing_refusal_header(api_client: Any, write_session: Session) -> None:
    """검색 노출 차단이 보안 요구사항이다 (PRD §8.4)."""
    token = curator_token(api_client, write_session)
    for url in ("/public/landing", "/system/health", "/admin/summary"):
        response = api_client.http.get(url, headers=auth_headers(token, csrf=False))
        assert "noindex" in response.headers["X-Robots-Tag"]

"""소셜 로그인의 순수 로직 (소셜 문서 §4).

여기서 검사하는 것은 **외부 없이 확인할 수 있는 방어**다 — 열린 리다이렉트, PKCE 변환,
티켓 봉인. 제공자와의 왕복은 `tests/integration/test_social_routes.py`가 맡는다.
"""

from __future__ import annotations

import base64
import hashlib

import pytest

from chalicelib.config.oauth import PROVIDERS, redirect_uri, spec_of
from chalicelib.core.security import (
    LinkTicket,
    OAuthTicket,
    build_oauth_link_cookie,
    build_oauth_state_cookie,
    code_challenge_of,
    new_state_secret,
    read_oauth_link_ticket,
    read_oauth_state_ticket,
)
from chalicelib.services.social_auth_service import DEFAULT_NEXT_PATH, safe_next_path


def _cookie_value(cookie: str) -> str:
    return cookie.split("=", 1)[1].split(";", 1)[0]


# ── 열린 리다이렉트 ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        # 프로토콜 상대 URL. 브라우저는 이것을 **다른 호스트로** 해석한다 —
        # "슬래시로 시작하는가"만 보는 검사가 놓치는 바로 그 형태다.
        "//evil.example.com",
        "/\\evil.example.com",
        "/%2fevil.example.com",
        "https://evil.example.com",
        "javascript:alert(1)",
        "gallery",
    ],
)
def test_next_path_falls_back_when_it_could_leave_the_app(raw: str | None) -> None:
    assert safe_next_path(raw) == DEFAULT_NEXT_PATH


@pytest.mark.parametrize("raw", ["/gallery", "/archive/2026-08-27", "/settings?tab=notify"])
def test_next_path_keeps_internal_routes(raw: str) -> None:
    assert safe_next_path(raw) == raw


# ── PKCE ───────────────────────────────────────────────────────────────────


def test_code_challenge_is_base64url_sha256_without_padding() -> None:
    """RFC 7636 §4.2. 패딩 `=`가 남으면 제공자가 challenge 불일치로 거부한다."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    challenge = code_challenge_of(verifier)
    assert challenge == expected
    assert "=" not in challenge


def test_state_secrets_are_unpredictable() -> None:
    assert len({new_state_secret() for _ in range(50)}) == 50


# ── 티켓 봉인 ──────────────────────────────────────────────────────────────


def test_state_ticket_round_trips() -> None:
    ticket = OAuthTicket(provider="kakao", state="s", code_verifier="v", nonce="n", next_path="/gallery")
    restored = read_oauth_state_ticket(_cookie_value(build_oauth_state_cookie(ticket, ttl_seconds=600)))
    assert restored == ticket


def test_link_ticket_round_trips() -> None:
    ticket = LinkTicket(
        provider="google",
        provider_uid="1234567890",
        email="a@example.com",
        display_name="이름",
        next_path="/gallery",
    )
    restored = read_oauth_link_ticket(_cookie_value(build_oauth_link_cookie(ticket, ttl_seconds=600)))
    assert restored == ticket


def test_a_state_ticket_is_not_accepted_as_a_link_ticket() -> None:
    """용도가 다른 티켓을 바꿔 쓰지 못한다.

    둘 다 같은 비밀로 서명되므로 용도 클레임이 없으면 인가 왕복 티켓을 그대로 연결
    티켓으로 제출할 수 있다 — `provider_uid`를 사용자가 고르게 되는 셈이다.
    """
    cookie = build_oauth_state_cookie(
        OAuthTicket(provider="kakao", state="s", code_verifier="v", nonce="n", next_path="/"),
        ttl_seconds=600,
    )
    assert read_oauth_link_ticket(_cookie_value(cookie)) is None


def test_expired_and_forged_tickets_are_indistinguishable_none() -> None:
    expired = build_oauth_state_cookie(
        OAuthTicket(provider="kakao", state="s", code_verifier="v", nonce="n", next_path="/"),
        ttl_seconds=-1,
    )
    assert read_oauth_state_ticket(_cookie_value(expired)) is None
    assert read_oauth_state_ticket("not-a-jwt") is None
    assert read_oauth_state_ticket(None) is None


# ── 제공자 서술자 ──────────────────────────────────────────────────────────


def test_every_provider_declares_a_complete_descriptor() -> None:
    """서술자가 흐름 코드의 유일한 제공자 지식이다. 빈칸이 있으면 런타임에 드러난다."""
    for provider, spec in PROVIDERS.items():
        assert spec.provider == provider
        assert spec.label
        for url in (spec.authorize_url, spec.token_url, spec.profile_url, spec.jwks_url):
            assert url.startswith("https://"), f"{provider}: {url}"
        assert spec.issuer.startswith("https://")
        assert "openid" in spec.scope.split(), f"{provider}: id_token 검증에 openid 가 필요하다"


def test_unknown_provider_has_no_descriptor() -> None:
    assert spec_of("naver") is None


class _FakeSettings:
    """`settings`는 frozen dataclass라 필드를 갈아끼울 수 없다. 참조를 통째로 바꾼다."""

    def __init__(self, base: str | None) -> None:
        self.social_redirect_base_url = base

    def social_enabled(self, provider: str) -> bool:
        return bool(self.social_redirect_base_url)


def test_redirect_uri_is_none_without_a_configured_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    """오리진이 없으면 콜백 URI를 만들 수 없다. 절반만 켜진 상태로 두지 않는다."""
    import chalicelib.config.oauth as oauth_config

    monkeypatch.setattr(oauth_config, "settings", _FakeSettings(None))
    assert redirect_uri("kakao") is None


def test_redirect_uri_matches_the_value_registered_with_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """제공자 콘솔에 등록하는 값과 **글자 그대로** 같아야 한다(소셜 문서 §7).

    끝의 슬래시 하나가 `//api/...`를 만들고, 그것만으로 제공자가 거부한다.
    """
    import chalicelib.config.oauth as oauth_config

    monkeypatch.setattr(oauth_config, "settings", _FakeSettings("https://gallery-k.example.com"))
    assert redirect_uri("kakao") == "https://gallery-k.example.com/api/auth/social/kakao/callback"
    assert redirect_uri("google") == "https://gallery-k.example.com/api/auth/social/google/callback"


# ── 토큰 교환 페이로드 ─────────────────────────────────────────────────────
#
# 카카오는 콘솔에서 client_secret 을 **켤 수 있다.** 켜 두면 이 파라미터 없이는 토큰
# 교환이 거부되며, 실패는 사용자가 동의를 마치고 돌아온 뒤에야 드러난다.
# 아래 두 검사가 그 파라미터를 코드에 못박는다.


class _FakeResponse:
    status_code = 200

    @staticmethod
    def json() -> dict[str, str]:
        return {"access_token": "at", "id_token": "idt"}


def _capture_exchange(monkeypatch: pytest.MonkeyPatch, *, client_secret: str | None) -> dict:
    from chalicelib.integrations import oauth as oauth_client

    captured: dict = {}

    def _post(url: str, data: dict, headers: dict, timeout: int) -> _FakeResponse:
        captured["url"] = url
        captured["data"] = dict(data)
        return _FakeResponse()

    monkeypatch.setattr(oauth_client.requests, "post", _post)
    oauth_client.exchange_code(
        PROVIDERS["kakao"],
        code="auth-code",
        redirect_uri="https://gallery-k.example.com/api/auth/social/kakao/callback",
        client_id="client-id",
        client_secret=client_secret,
        code_verifier="verifier",
    )
    return captured


def test_token_exchange_sends_the_client_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """콘솔에서 client_secret 을 켠 제공자는 이 파라미터 없이는 코드를 교환해 주지 않는다."""
    captured = _capture_exchange(monkeypatch, client_secret="secret-from-env")

    assert captured["url"] == PROVIDERS["kakao"].token_url
    assert captured["data"]["client_secret"] == "secret-from-env"
    # 함께 가야 하는 나머지 — 하나라도 빠지면 교환이 거부된다.
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["client_id"] == "client-id"
    assert captured["data"]["code_verifier"] == "verifier"


def test_token_exchange_omits_the_client_secret_when_it_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """카카오는 콘솔에서 끌 수 있다. 그때 빈 문자열을 보내면 오히려 거부된다."""
    captured = _capture_exchange(monkeypatch, client_secret=None)
    assert "client_secret" not in captured["data"]

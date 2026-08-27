"""소셜 로그인 왕복 (API 문서 §6.11–§6.15, 소셜 문서 §3).

제공자와의 HTTP만 대역으로 바꾸고 **나머지는 실제 경로를 그대로 탄다** — 쿠키 발급,
`state` 대조, 세션 발급, DB 반영이 전부 진짜다. 대역이 흉내 내는 것은 카카오·구글이
돌려주는 JSON 두 개뿐이다.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.config.constants import OAUTH_LINK_COOKIE_NAME, OAUTH_STATE_COOKIE_NAME
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, SocialIdentity

from .helpers import CSRF, auth_headers, json_body, session_token, set_cookie_values, signup

pytestmark = pytest.mark.integration

PROVIDER = "kakao"
UID = "3141592653"
ORIGIN = "https://gallery-k.example.com"


class _FakeSettings:
    """`settings`는 frozen dataclass라 필드를 바꿀 수 없다. 참조를 통째로 건다."""

    social_redirect_base_url = ORIGIN

    def social_enabled(self, provider: str) -> bool:
        return provider == PROVIDER

    def social_client_id(self, provider: str) -> str | None:
        return "client-id" if provider == PROVIDER else None

    def social_client_secret(self, provider: str) -> str | None:
        return "client-secret"


@pytest.fixture()
def social_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """제공자 자격이 있는 것처럼 만든다. 여기까지가 설정의 몫이다."""
    import chalicelib.config.oauth as oauth_config
    import chalicelib.services.social_auth_service as service

    fake = _FakeSettings()
    monkeypatch.setattr(oauth_config, "settings", fake)
    monkeypatch.setattr(service, "settings", fake)


@pytest.fixture()
def fake_provider(monkeypatch: pytest.MonkeyPatch, social_enabled: None) -> dict[str, Any]:
    """제공자 응답 대역. `calls`에 무엇이 오갔는지 남겨 검증에 쓴다."""
    import chalicelib.services.social_auth_service as service

    calls: dict[str, Any] = {"exchange": None, "verify": None, "profile_called": False}

    def _exchange(spec: Any, **kwargs: Any) -> Any:
        calls["exchange"] = kwargs
        return service.oauth_client.TokenResponse(access_token="at", id_token="idt")

    def _verify(spec: Any, **kwargs: Any) -> dict[str, Any]:
        calls["verify"] = kwargs
        return {"sub": UID, "nonce": kwargs["nonce"]}

    def _profile(spec: Any, **kwargs: Any) -> dict[str, Any]:
        # OIDC가 꺼진 제공자 설정에서만 타는 대체 경로다. scope가 `openid`뿐이라
        # 실제 응답에도 식별자 말고는 담기지 않는다.
        calls["profile_called"] = True
        return {"id": UID}

    monkeypatch.setattr(service.oauth_client, "exchange_code", _exchange)
    monkeypatch.setattr(service.oauth_client, "verify_id_token", _verify)
    monkeypatch.setattr(service.oauth_client, "fetch_profile", _profile)
    return calls


def _cookie(response: Any, name: str) -> str | None:
    for cookie in set_cookie_values(response):
        key, _, rest = cookie.partition("=")
        if key == name:
            return rest.split(";", 1)[0] or None
    return None


def _start(client: Any, next_path: str = "/gallery") -> Any:
    return client.http.get(f"/auth/social/{PROVIDER}/start?next={next_path}")


def _callback(client: Any, *, state: str | None, state_cookie: str | None) -> Any:
    headers = {"Cookie": f"{OAUTH_STATE_COOKIE_NAME}={state_cookie}"} if state_cookie else {}
    query = f"?code=auth-code&state={state}" if state else "?code=auth-code"
    return client.http.get(f"/auth/social/{PROVIDER}/callback{query}", headers=headers)


def _authorize_state(response: Any) -> str:
    location = response.headers["Location"]
    return location.split("state=", 1)[1].split("&", 1)[0]


# ── 제공자 목록 ────────────────────────────────────────────────────────────


def test_providers_lists_only_configured_ones(api_client: Any, social_enabled: None) -> None:
    body = api_client.http.get("/auth/social/providers").json_body
    assert [p["provider"] for p in body["data"]["providers"]] == [PROVIDER]
    assert body["data"]["providers"][0]["start_url"] == f"/api/auth/social/{PROVIDER}/start"


class _NoCredentials:
    """자격이 하나도 없는 상태. 실제 `.env`를 읽지 않는다."""

    social_redirect_base_url = None

    def social_enabled(self, provider: str) -> bool:
        return False


def test_providers_is_empty_without_credentials(api_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """키가 없으면 목록이 비고, 화면은 소셜 영역 자체를 그리지 않는다(소셜 문서 §8).

    설정을 **명시적으로 비운다.** 개발자의 `.env`에 기대면 그 파일을 채우는 순간
    테스트 결과가 바뀐다 — 실제로 그렇게 깨진 적이 있다.
    """
    import chalicelib.config.oauth as oauth_config

    monkeypatch.setattr(oauth_config, "settings", _NoCredentials())

    body = api_client.http.get("/auth/social/providers").json_body
    assert body["data"]["providers"] == []


# ── ① 인가 시작 ────────────────────────────────────────────────────────────


def test_start_redirects_with_pkce_and_seals_the_secret_in_a_cookie(
    api_client: Any, social_enabled: None
) -> None:
    """URL에는 challenge만, verifier는 쿠키에만 — 그것이 PKCE의 전부다."""
    response = _start(api_client)

    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.startswith("https://kauth.kakao.com/oauth/authorize?")
    assert "code_challenge_method=S256" in location
    assert "code_challenge=" in location
    assert "code_verifier" not in location
    assert f"redirect_uri={ORIGIN.replace(':', '%3A').replace('/', '%2F')}" in location

    cookie = next(c for c in set_cookie_values(response) if c.startswith(OAUTH_STATE_COOKIE_NAME))
    assert "HttpOnly" in cookie
    # 리다이렉트 왕복을 견디는 것은 Lax다. None으로 내리면 CSRF 방어가 한 겹 사라진다.
    assert "SameSite=Lax" in cookie


def test_start_rejects_an_unknown_provider(api_client: Any, social_enabled: None) -> None:
    response = api_client.http.get("/auth/social/naver/start")
    assert response.status_code == 302
    assert "social_error=SOCIAL_PROVIDER_UNKNOWN" in response.headers["Location"]


def test_start_refuses_to_send_the_user_off_site(api_client: Any, social_enabled: None) -> None:
    """`next`가 외부를 가리켜도 인가는 시작되지만, 돌아올 곳은 앱 안이다."""
    response = _start(api_client, next_path="//evil.example.com")
    assert response.status_code == 302
    state_cookie = _cookie(response, OAUTH_STATE_COOKIE_NAME)

    from chalicelib.core.security import read_oauth_state_ticket

    ticket = read_oauth_state_ticket(state_cookie)
    assert ticket is not None
    assert ticket.next_path == "/gallery"


# ── ② 콜백 — state 방어 ────────────────────────────────────────────────────


def test_callback_rejects_a_mismatched_state(api_client: Any, fake_provider: dict[str, Any]) -> None:
    """로그인 CSRF 방어. **토큰 교환을 시도조차 하지 않는다.**"""
    state_cookie = _cookie(_start(api_client), OAUTH_STATE_COOKIE_NAME)

    response = _callback(api_client, state="attacker-state", state_cookie=state_cookie)

    assert response.status_code == 302
    assert "social_error=SOCIAL_STATE_INVALID" in response.headers["Location"]
    assert fake_provider["exchange"] is None, "state가 틀렸는데 토큰을 교환했다"


def test_callback_rejects_a_missing_cookie(api_client: Any, fake_provider: dict[str, Any]) -> None:
    response = _callback(api_client, state="whatever", state_cookie=None)
    assert "social_error=SOCIAL_STATE_INVALID" in response.headers["Location"]
    assert fake_provider["exchange"] is None


def test_callback_returns_quietly_when_the_user_cancels(api_client: Any, social_enabled: None) -> None:
    """동의 화면에서 그만둔 것은 실패가 아니다. 오류 문구를 띄우지 않는다."""
    response = api_client.http.get(f"/auth/social/{PROVIDER}/callback?error=access_denied")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_callback_sends_the_verifier_and_checks_the_nonce(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    start = _start(api_client)
    state_cookie = _cookie(start, OAUTH_STATE_COOKIE_NAME)

    _callback(api_client, state=_authorize_state(start), state_cookie=state_cookie)

    assert fake_provider["exchange"]["code_verifier"], "PKCE verifier가 교환에 실리지 않았다"
    # 설정 → 서비스 → 어댑터로 client_secret 이 내려가는지. 카카오 콘솔에서 이 값을
    # 켜 두면 없이는 교환이 거부되고, 그 실패는 사용자가 동의를 마친 뒤에야 드러난다.
    assert fake_provider["exchange"]["client_secret"] == "client-secret"
    assert fake_provider["exchange"]["redirect_uri"] == (f"{ORIGIN}/api/auth/social/{PROVIDER}/callback")
    assert fake_provider["verify"]["nonce"], "id_token nonce 대조가 없었다"


def test_authorize_requests_only_the_openid_scope(api_client: Any, social_enabled: None) -> None:
    """닉네임·이메일을 **요청하지 않는다**(PRD §8.4 최소 수집).

    화면 어디에서도 쓰지 않는 값이라 받아 봐야 지킬 책임만 늘어나고, 제공자 콘솔의
    동의항목·동의 목적 심사도 따라온다. 받지 않으면 그 전부가 사라진다.
    """
    location = _start(api_client).headers["Location"]

    assert "scope=openid&" in location or location.endswith("scope=openid")
    assert "profile_nickname" not in location
    assert "account_email" not in location


def test_profile_api_is_not_called_when_the_id_token_carries_the_subject(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    """`id_token`으로 신원이 확정되면 프로필 API를 부르지 않는다.

    부르면 쓰지도 않을 데이터를 받게 된다. **받지 않는 것이 최소 수집이다.**
    """
    start = _start(api_client)
    _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )

    assert fake_provider["verify"] is not None, "id_token 검증을 하지 않았다"
    assert fake_provider["profile_called"] is False, "불필요한 프로필 조회가 나갔다"


def test_identity_is_stored_without_email_or_nickname(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    """받지 않았으므로 저장될 것도 없다. 컬럼은 남아 있되 비어 있다."""
    api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    identity = q.fetch_one(write_session, SocialIdentity, where={"provider_uid": UID})
    assert identity is not None
    assert identity.email is None
    assert identity.display_name is None


@pytest.fixture()
def provider_without_oidc(monkeypatch: pytest.MonkeyPatch, social_enabled: None) -> dict[str, Any]:
    """제공자 콘솔에서 **OpenID Connect가 꺼진** 상태. `id_token`이 오지 않는다."""
    import chalicelib.services.social_auth_service as service

    calls: dict[str, Any] = {"verify_called": False, "profile_called": False}

    def _exchange(spec: Any, **kwargs: Any) -> Any:
        return service.oauth_client.TokenResponse(access_token="at", id_token=None)

    def _verify(spec: Any, **kwargs: Any) -> dict[str, Any]:
        calls["verify_called"] = True
        return {}

    def _profile(spec: Any, **kwargs: Any) -> dict[str, Any]:
        calls["profile_called"] = True
        # 동의항목 없이도 카카오는 식별자를 준다.
        return {"id": UID}

    monkeypatch.setattr(service.oauth_client, "exchange_code", _exchange)
    monkeypatch.setattr(service.oauth_client, "verify_id_token", _verify)
    monkeypatch.setattr(service.oauth_client, "fetch_profile", _profile)
    return calls


def test_login_still_works_when_the_provider_has_no_oidc(
    api_client: Any, provider_without_oidc: dict[str, Any]
) -> None:
    """`id_token`이 없으면 프로필 API의 식별자로 대체한다.

    **OIDC를 켜는 것은 우리 코드의 요구가 아니다.** 켜면 서명 검증과 nonce 리플레이
    방어가 한 겹 더 붙고, 꺼도 로그인 자체는 성립한다 — 어느 쪽인지가 이 검사로 드러난다.
    """
    start = _start(api_client)
    response = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/link", "신원 확정에 실패했다"
    assert _cookie(response, OAUTH_LINK_COOKIE_NAME), "연결 티켓이 발급되지 않았다"

    assert provider_without_oidc["verify_called"] is False, "없는 id_token을 검증하려 했다"
    assert provider_without_oidc["profile_called"] is True, "대체 경로를 타지 않았다"


def test_identity_uses_the_profile_id_when_there_is_no_id_token(
    api_client: Any, write_session: Session, provider_without_oidc: dict[str, Any]
) -> None:
    """`id_token`이 없으면 `/v2/user/me`의 `id`가 그대로 `provider_uid`가 된다.

    **이 검사가 보장하지 못하는 것** — 제공자의 `id_token.sub`와 프로필 `id`가 같은
    값이라는 사실은 제공자의 약속이지 우리 코드의 성질이 아니다. 두 값이 다른
    제공자에서 콘솔 스위치를 나중에 끄면 같은 사람이 다른 계정이 된다(소셜 문서 §6.2).
    """
    api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    identity = q.fetch_one(write_session, SocialIdentity, where={"user_id__isnull": False})
    assert identity is not None
    assert identity.provider_uid == UID


# ── ③ 미연결 → A-4 연결 화면 ───────────────────────────────────────────────


def test_first_time_social_login_goes_to_the_link_screen(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    """**자동 가입하지 않는다.** 전화번호가 필요하다(소셜 문서 SA-2)."""
    start = _start(api_client)
    response = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/link"
    assert _cookie(response, OAUTH_LINK_COOKIE_NAME)
    assert session_token(response) is None, "계정 없이 세션이 발급되었다"


def _link_cookie(api_client: Any) -> str:
    start = _start(api_client)
    callback = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )
    value = _cookie(callback, OAUTH_LINK_COOKIE_NAME)
    assert value is not None
    return value


def _link_headers(ticket: str) -> dict[str, str]:
    return {**CSRF, "Cookie": f"{OAUTH_LINK_COOKIE_NAME}={ticket}"}


# ── ④ 기존 계정에 연결 ─────────────────────────────────────────────────────


def test_link_requires_the_account_password(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    """번호만으로 연결되면 남의 번호를 적어 계정을 가져갈 수 있다."""
    signup(api_client, phone="01011112222", password="password123", name="기존회원")
    ticket = _link_cookie(api_client)

    wrong = api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(ticket),
        body=json_body({"phone": "01011112222", "password": "wrong-password"}),
    )
    assert wrong.status_code == 401
    assert wrong.json_body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert q.count(write_session, SocialIdentity) == 0


def test_link_hides_whether_the_account_exists(api_client: Any, fake_provider: dict[str, Any]) -> None:
    """미가입 번호와 비밀번호 불일치가 **같은 응답**이다(API 문서 §5.2)."""
    ticket = _link_cookie(api_client)
    response = api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(ticket),
        body=json_body({"phone": "01099998888", "password": "password123"}),
    )
    assert response.status_code == 401
    assert response.json_body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_link_attaches_the_identity_and_issues_a_session(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    signup(api_client, phone="01011112222", password="password123", name="기존회원")
    ticket = _link_cookie(api_client)

    response = api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(ticket),
        body=json_body({"phone": "01011112222", "password": "password123"}),
    )

    assert response.status_code == 200
    assert session_token(response), "연결 후 세션이 발급되지 않았다"
    identity = q.fetch_one(write_session, SocialIdentity, where={"provider_uid": UID})
    assert identity is not None
    assert identity.provider == PROVIDER
    # 티켓은 1회용이다. 재사용이 곧 리플레이다.
    assert any(c.startswith(f"{OAUTH_LINK_COOKIE_NAME}=;") for c in set_cookie_values(response)), (
        "연결 티켓이 폐기되지 않았다"
    )


def test_a_second_login_with_a_linked_account_never_reaches_the_link_screen(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    """연결이 끝난 소셜로 다시 들어오면 **연결 티켓이 발급되지 않는다.**

    이것이 `SOCIAL_ALREADY_LINKED`가 평상시 나오지 않는 이유다 — 정상 흐름에서는
    티켓을 다시 받을 길이 없다. 그 코드는 아래 경합 상황을 위한 가드다.
    """
    signup(api_client, phone="01011112222", password="password123", name="첫째")
    api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01011112222", "password": "password123"}),
    )

    start = _start(api_client)
    response = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )
    assert response.headers["Location"] == "/gallery"
    assert _cookie(response, OAUTH_LINK_COOKIE_NAME) is None


def test_linking_an_already_linked_social_account_is_refused(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    """티켓을 손에 쥔 채 다른 계정에 붙이려는 경합. `(provider, uid)`가 UNIQUE다.

    두 탭에서 동시에 진행하면 실제로 일어난다 — 먼저 발급된 티켓이 나중까지 살아 있다.
    **어느 계정에 붙어 있는지는 알려주지 않는다**(SA-5).
    """
    from chalicelib.config.oauth import LINK_TICKET_TTL_SECONDS
    from chalicelib.core.security import LinkTicket, build_oauth_link_cookie

    signup(api_client, phone="01011112222", password="password123", name="첫째")
    api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01011112222", "password": "password123"}),
    )
    signup(api_client, phone="01033334444", password="password123", name="둘째")

    stale = build_oauth_link_cookie(
        LinkTicket(provider=PROVIDER, provider_uid=UID, email=None, display_name=None, next_path="/gallery"),
        ttl_seconds=LINK_TICKET_TTL_SECONDS,
    )
    response = api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(stale.split("=", 1)[1].split(";", 1)[0]),
        body=json_body({"phone": "01033334444", "password": "password123"}),
    )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == "SOCIAL_ALREADY_LINKED"
    assert "01011112222" not in str(response.json_body)


def test_link_without_a_ticket_is_refused(api_client: Any, social_enabled: None) -> None:
    """A-4 화면 주소를 직접 쳐서 들어올 수 없다."""
    response = api_client.http.post(
        "/auth/social/link",
        headers=CSRF,
        body=json_body({"phone": "01011112222", "password": "password123"}),
    )
    assert response.status_code == 400
    assert response.json_body["error"]["code"] == "SOCIAL_LINK_EXPIRED"


# ── ⑤ 소셜 신규 가입 ───────────────────────────────────────────────────────


def test_social_signup_creates_an_account_without_a_password(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    ticket = _link_cookie(api_client)

    response = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(ticket),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )

    assert response.status_code == 201
    assert session_token(response)
    assert response.json_body["data"]["user"]["has_password"] is False

    user = q.fetch_one(write_session, AppUser, where={"phone": "01055556666"})
    assert user is not None
    assert user.password_hash is None
    assert user.created_via == "social"


def test_social_signup_respects_the_signup_lock(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    """가입 잠금의 뒷문이 되면 폐쇄형 서비스라는 전제가 깨진다."""
    from chalicelib.db.models import AppSetting
    from chalicelib.services import setting_service

    q.insert(
        write_session,
        AppSetting,
        {
            "key": setting_service.SettingKey.SIGNUP_OPEN,
            "value": False,
            "value_type": "boolean",
            "description": "테스트",
        },
    )
    write_session.commit()
    setting_service.invalidate_cache()

    response = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    assert response.status_code == 403
    assert response.json_body["error"]["code"] == "SIGNUP_CLOSED"


def test_social_signup_on_a_taken_phone_points_at_linking(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    signup(api_client, phone="01011112222", password="password123", name="기존회원")

    response = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01011112222", "name": "새회원", "agreed_terms": True}),
    )
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == "SIGNUP_PHONE_TAKEN"


# ── ⑥ 두 번째 로그인 — 연결된 계정 ─────────────────────────────────────────


def test_returning_social_login_goes_straight_to_the_gallery(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )

    start = _start(api_client, next_path="/archive")
    response = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/archive"
    assert session_token(response)


def test_blocked_member_cannot_enter_through_the_social_door(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    """차단 사실을 알리지 않는다 — 전화번호 로그인과 **같은 문으로 나간다**."""
    api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    user = q.fetch_one(write_session, AppUser, where={"phone": "01055556666"})
    assert user is not None
    from chalicelib.core.timeutil import now_utc

    q.update(
        write_session,
        AppUser,
        where={"id": user.id},
        values={"is_blocked": True, "blocked_at": now_utc()},
    )
    write_session.commit()

    start = _start(api_client)
    response = _callback(
        api_client,
        state=_authorize_state(start),
        state_cookie=_cookie(start, OAUTH_STATE_COOKIE_NAME),
    )
    assert "social_error=AUTH_INVALID_CREDENTIALS" in response.headers["Location"]
    assert session_token(response) is None


# ── ⑦ 연결 관리 (API 문서 §8.7·§8.8) ───────────────────────────────────────


def test_last_login_method_cannot_be_unlinked(api_client: Any, fake_provider: dict[str, Any]) -> None:
    """해제하면 들어올 길이 0이 된다(SA-6)."""
    created = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    token = session_token(created)

    listed = api_client.http.get("/me/social-identities", headers=auth_headers(token, csrf=False))
    assert listed.json_body["data"]["can_unlink"] is False
    identity_id = listed.json_body["data"]["identities"][0]["id"]

    response = api_client.http.delete(f"/me/social-identities/{identity_id}", headers=auth_headers(token))
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == "SOCIAL_LAST_IDENTITY"


def test_a_member_with_a_password_can_unlink(
    api_client: Any, write_session: Session, fake_provider: dict[str, Any]
) -> None:
    signup(api_client, phone="01011112222", password="password123", name="기존회원")
    linked = api_client.http.post(
        "/auth/social/link",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01011112222", "password": "password123"}),
    )
    token = session_token(linked)

    listed = api_client.http.get("/me/social-identities", headers=auth_headers(token, csrf=False))
    assert listed.json_body["data"]["can_unlink"] is True
    identity_id = listed.json_body["data"]["identities"][0]["id"]

    response = api_client.http.delete(f"/me/social-identities/{identity_id}", headers=auth_headers(token))
    assert response.status_code == 200
    assert q.count(write_session, SocialIdentity) == 0


def test_identity_list_never_leaks_provider_tokens(api_client: Any, fake_provider: dict[str, Any]) -> None:
    """제공자 access·refresh token은 저장하지도 반환하지도 않는다(SA-3)."""
    created = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    listed = api_client.http.get(
        "/me/social-identities", headers=auth_headers(session_token(created), csrf=False)
    )
    body = str(listed.json_body)
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert "idt" not in body


def test_unlinking_someone_elses_identity_answers_absent(
    api_client: Any, fake_provider: dict[str, Any]
) -> None:
    """남의 연결 id로 존재를 떠볼 수 없다."""
    created = api_client.http.post(
        "/auth/social/signup",
        headers=_link_headers(_link_cookie(api_client)),
        body=json_body({"phone": "01055556666", "name": "새회원", "agreed_terms": True}),
    )
    listed = api_client.http.get(
        "/me/social-identities", headers=auth_headers(session_token(created), csrf=False)
    )
    identity_id = listed.json_body["data"]["identities"][0]["id"]

    other = signup(api_client, phone="01077778888", password="password123", name="남")
    response = api_client.http.delete(
        f"/me/social-identities/{identity_id}", headers=auth_headers(session_token(other))
    )
    assert response.status_code == 404

"""인증 API — 실제 DB (API 문서 §6, PRD §6.2·§6.4)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from chalicelib.config.constants import SESSION_COOKIE_NAME
from chalicelib.core.errors import ErrorCode
from chalicelib.db import query as q
from chalicelib.db.models import AppUser, AuthThrottle, NotificationLog
from chalicelib.schemas.auth import SessionOut, SignupOut, UserOut
from chalicelib.services import setting_service

from .helpers import CSRF, auth_headers, json_body, login, session_token, signup

pytestmark = pytest.mark.integration


def test_signup_logs_the_member_in(api_client: Any) -> None:
    response = signup(api_client)
    assert response.status_code == 201
    body = response.json_body
    data = SignupOut.model_validate(body["data"])
    assert data.is_first_login is True
    assert data.user.phone_masked == "010-****-5678"
    assert data.user.notify_enabled is True
    assert data.user.notify_at == "07:30"
    assert session_token(response)


def test_signup_never_returns_the_full_phone_number(api_client: Any) -> None:
    """전체 전화번호는 어떤 관람자 API에서도 반환하지 않는다 (API 문서 §3.6)."""
    response = signup(api_client, phone="010-1234-5678")
    assert "01012345678" not in str(response.json_body)


def test_signup_rejects_a_taken_phone_number(api_client: Any) -> None:
    signup(api_client)
    response = signup(api_client, name="다른사람")
    assert response.status_code == 409
    assert response.json_body["error"]["code"] == ErrorCode.SIGNUP_PHONE_TAKEN


def test_signup_is_refused_while_locked(api_client: Any, write_session: Session) -> None:
    from chalicelib.db.models import AppSetting

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

    response = signup(api_client)
    assert response.status_code == 403
    assert response.json_body["error"]["code"] == ErrorCode.SIGNUP_CLOSED


def test_signup_queues_a_curator_notification(api_client: Any, write_session: Session) -> None:
    """누군가 가입하면 큐레이터에게 알림이 간다 (PRD §6.4)."""
    q.insert(
        write_session,
        AppUser,
        {
            "phone": "01000000000",
            "password_hash": "x" * 60,
            "name": "큐레이터",
            "role": "curator",
            "created_via": "curator",
        },
    )
    write_session.commit()

    signup(api_client)
    rows = q.fetch(write_session, NotificationLog, where={"kind": "curator_signup"})
    assert len(rows) == 1
    assert rows[0].payload == {"member_name": "관람자"}
    # 전화번호는 알림 이력에도 담지 않는다.
    assert "01012345678" not in str(rows[0].payload)


def test_short_password_is_refused_by_policy(api_client: Any) -> None:
    response = signup(api_client, password="short")
    assert response.status_code == 422
    codes = {item["code"] for item in response.json_body["error"]["field_errors"]}
    assert codes == {"TOO_SHORT"}


def test_login_returns_a_session_cookie_with_the_documented_attributes(api_client: Any) -> None:
    signup(api_client)
    response = login(api_client, phone="01012345678", password="password123")
    assert response.status_code == 200
    UserOut.model_validate(response.json_body["data"])

    raw = response.headers["Set-Cookie"]
    cookie = raw if isinstance(raw, str) else raw[0]
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    # 토큰은 바디에 담기지 않는다.
    assert "token" not in str(response.json_body["data"])


def test_unknown_blocked_and_wrong_password_answer_identically(
    api_client: Any, write_session: Session
) -> None:
    """세 경우가 구분되면 전화번호부로 회원 명단을 복원할 수 있다 (API 문서 §5.2)."""
    signup(api_client, phone="01011112222", password="password123")
    blocked = q.insert(
        write_session,
        AppUser,
        {
            "phone": "01033334444",
            "password_hash": "x" * 60,
            "name": "차단회원",
            "is_blocked": True,
            "blocked_at": "2026-08-27T00:00:00Z",
        },
    )
    write_session.commit()
    assert blocked.is_blocked

    unknown = login(api_client, phone="01099998888", password="password123")
    wrong = login(api_client, phone="01011112222", password="wrongpassword")
    blocked_response = login(api_client, phone="01033334444", password="password123")

    for response in (unknown, wrong, blocked_response):
        assert response.status_code == 401
        assert response.json_body["error"]["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS
        assert response.json_body["error"]["message"] == "전화번호 또는 비밀번호가 맞지 않습니다."
        assert response.json_body["error"]["details"] is None


def test_repeated_failures_lock_the_account_for_ten_minutes(api_client: Any, write_session: Session) -> None:
    signup(api_client, phone="01011112222", password="password123")

    for _ in range(5):
        response = login(api_client, phone="01011112222", password="wrong")
    assert response.status_code == 429
    assert response.json_body["error"]["code"] == ErrorCode.AUTH_TOO_MANY_ATTEMPTS
    assert response.json_body["error"]["details"]["retry_after_seconds"] == 600
    assert response.headers["Retry-After"] == "600"

    # 잠긴 뒤에는 올바른 비밀번호도 통과하지 않는다.
    correct = login(api_client, phone="01011112222", password="password123")
    assert correct.status_code == 429


def test_throttle_counter_survives_the_failed_request_transaction(
    api_client: Any, write_session: Session
) -> None:
    """401로 끝난 요청이 롤백되어도 시도 카운터는 남아야 한다."""
    signup(api_client, phone="01011112222", password="password123")
    login(api_client, phone="01011112222", password="wrong")

    row = q.fetch_one(write_session, AuthThrottle, where={"throttle_key": "login:01011112222"})
    assert row is not None
    assert row.fail_count == 1


def test_successful_login_clears_the_counter(api_client: Any, write_session: Session) -> None:
    signup(api_client, phone="01011112222", password="password123")
    login(api_client, phone="01011112222", password="wrong")
    login(api_client, phone="01011112222", password="password123")

    assert q.count(write_session, AuthThrottle, where={"throttle_key": "login:01011112222"}) == 0


def test_session_endpoint_answers_for_anonymous_visitors(api_client: Any) -> None:
    response = api_client.http.get("/auth/session")
    assert response.status_code == 200
    data = SessionOut.model_validate(response.json_body["data"])
    assert data.is_authenticated is False
    assert data.user is None


def test_session_endpoint_returns_the_member_and_renews_the_cookie(api_client: Any) -> None:
    token = session_token(signup(api_client))
    response = api_client.http.get("/auth/session", headers=auth_headers(token, csrf=False))
    data = SessionOut.model_validate(response.json_body["data"])
    assert data.is_authenticated is True
    assert data.user is not None
    assert session_token(response), "세션 확인 경로는 쿠키를 갱신한다"


def test_logout_expires_the_cookie(api_client: Any) -> None:
    token = session_token(signup(api_client))
    response = api_client.http.post("/auth/logout", headers=auth_headers(token), body=b"")
    assert response.status_code == 200
    raw = response.headers["Set-Cookie"]
    cookie = raw if isinstance(raw, str) else raw[0]
    assert "Max-Age=0" in cookie


def test_password_change_revokes_other_devices(api_client: Any) -> None:
    """`token_version` 증가로 다른 단말 세션이 끊긴다 (API 문서 §6.7)."""
    first = session_token(signup(api_client))
    second = session_token(login(api_client, phone="01012345678", password="password123"))

    changed = api_client.http.post(
        "/auth/password",
        headers=auth_headers(second),
        body=json_body({"current_password": "password123", "new_password": "newpassword456"}),
    )
    assert changed.status_code == 200
    renewed = session_token(changed)
    assert renewed and renewed != second

    stale = api_client.http.get("/me", headers=auth_headers(first, csrf=False))
    assert stale.status_code == 401
    assert stale.json_body["error"]["code"] == ErrorCode.AUTH_SESSION_REVOKED

    fresh = api_client.http.get("/me", headers=auth_headers(renewed, csrf=False))
    assert fresh.status_code == 200


def test_password_change_requires_the_current_password(api_client: Any) -> None:
    token = session_token(signup(api_client))
    response = api_client.http.post(
        "/auth/password",
        headers=auth_headers(token),
        body=json_body({"current_password": "wrong", "new_password": "newpassword456"}),
    )
    assert response.status_code == 401
    assert response.json_body["error"]["code"] == ErrorCode.PASSWORD_CURRENT_MISMATCH


def test_password_reset_request_answers_the_same_for_unknown_numbers(api_client: Any) -> None:
    """미가입 번호에도 동일한 성공 응답을 준다 (PRD §6.3)."""
    known = signup(api_client, phone="01011112222")
    assert known.status_code == 201

    for phone in ("01011112222", "01099998888"):
        response = api_client.http.post(
            "/auth/password/reset/request",
            headers=CSRF,
            body=json_body({"phone": phone}),
        )
        assert response.status_code == 200
        assert response.json_body["data"] == {
            "expires_in_seconds": 180,
            "resend_after_seconds": 60,
        }

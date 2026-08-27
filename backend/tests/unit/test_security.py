"""인증 원시 연산 (백엔드 문서 §13)."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from chalicelib.config.constants import PASSWORD_MAX_LENGTH, SESSION_COOKIE_NAME
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.security import (
    build_expired_session_cookie,
    build_session_cookie,
    decode_session_token,
    hash_password,
    issue_session_token,
    read_cookie,
    verify_password,
)
from chalicelib.core.timeutil import freeze_time, now_utc


def test_password_round_trip() -> None:
    stored = hash_password("올바른말고양이배터리")
    assert stored != "올바른말고양이배터리"
    assert verify_password("올바른말고양이배터리", stored) is True
    assert verify_password("틀린비밀번호", stored) is False


def test_full_length_korean_password_is_not_silently_truncated() -> None:
    """64자 한글은 192바이트다. bcrypt의 72바이트 절단을 sha256으로 접어 피한다."""
    base = "가" * PASSWORD_MAX_LENGTH
    stored = hash_password(base)
    assert verify_password(base, stored) is True
    # 절단되었다면 앞 24자만 같아도 통과했을 것이다.
    assert verify_password("가" * 24 + "나" * (PASSWORD_MAX_LENGTH - 24), stored) is False


def test_missing_hash_still_costs_a_verification() -> None:
    """미가입 번호와 비밀번호 불일치가 같은 경로를 타야 한다 (§5.2)."""
    assert verify_password("무엇이든", None) is False
    assert verify_password("무엇이든", "손상된해시") is False


def test_session_token_carries_the_documented_claims() -> None:
    user_id = uuid.uuid4()
    issued_at = dt.datetime(2026, 8, 27, tzinfo=dt.UTC)
    token, expires_at = issue_session_token(
        user_id=user_id, role="viewer", token_version=7, issued_at=issued_at
    )
    claims = decode_session_token(token)
    assert claims.user_id == user_id
    assert claims.role == "viewer"
    assert claims.token_version == 7
    assert (expires_at - issued_at).days == 90
    assert claims.jti


def test_sliding_renewal_triggers_within_thirty_days_of_expiry() -> None:
    # PyJWT는 서명 만료를 실제 시계로 검증하므로 발급은 현재 시각 기준으로 한다.
    # 갱신 판정만 우리 시계(`core.timeutil`)를 쓰며, 테스트는 그쪽을 고정한다.
    issued_at = now_utc()
    token, _ = issue_session_token(user_id=uuid.uuid4(), role="viewer", token_version=1, issued_at=issued_at)
    claims = decode_session_token(token)
    with freeze_time(issued_at + dt.timedelta(days=59)):
        assert claims.needs_renewal is False
    with freeze_time(issued_at + dt.timedelta(days=61)):
        assert claims.needs_renewal is True


def test_expired_token_is_distinguishable_from_forged_token() -> None:
    expired = issue_session_token(
        user_id=uuid.uuid4(),
        role="viewer",
        token_version=1,
        issued_at=dt.datetime(2020, 1, 1, tzinfo=dt.UTC),
    )[0]
    with pytest.raises(AppError) as caught:
        decode_session_token(expired)
    assert caught.value.code == ErrorCode.AUTH_SESSION_EXPIRED

    with pytest.raises(AppError) as caught:
        decode_session_token("not-a-token")
    assert caught.value.code == ErrorCode.AUTH_REQUIRED


def test_cookie_attributes_match_the_contract() -> None:
    cookie = build_session_cookie("TOKEN")
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=TOKEN")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Max-Age=7776000" in cookie
    assert "Max-Age=0" in build_expired_session_cookie()


def test_cookie_reader_picks_the_right_pair() -> None:
    header = f"other=1; {SESSION_COOKIE_NAME}=abc.def; trailing=2"
    assert read_cookie(header, SESSION_COOKIE_NAME) == "abc.def"
    assert read_cookie(None, SESSION_COOKIE_NAME) is None
    assert read_cookie("other=1", SESSION_COOKIE_NAME) is None

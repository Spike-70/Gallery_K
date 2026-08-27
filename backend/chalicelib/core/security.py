"""인증 원시 연산 (백엔드 문서 §13, API 문서 §2.7).

* 비밀번호는 bcrypt. **실패 경로도 동일한 시간이 걸리게 한다** — 미가입 번호와
  비밀번호 불일치의 응답 시간이 다르면 계정 존재 여부가 새어 나간다(§5.2).
* 세션 토큰은 JWT(HS256)이며 **HttpOnly 쿠키로만** 전달한다. 응답 바디에 넣지 않는다.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import Any, Final

import bcrypt
import jwt

from chalicelib.config.constants import (
    OAUTH_LINK_COOKIE_NAME,
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_MAX_AGE_SECONDS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH,
    SESSION_COOKIE_SAMESITE,
    SESSION_SLIDING_RENEW_WITHIN_SECONDS,
)
from chalicelib.config.settings import settings
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.ids import new_request_id
from chalicelib.core.timeutil import now_utc

_BCRYPT_ROUNDS: Final = 12

#: 미가입 번호에도 같은 시간이 걸리게 하는 더미 해시. 모듈 로드 시 1회 생성한다.
_DUMMY_HASH: Final[bytes] = bcrypt.hashpw(
    base64.b64encode(hashlib.sha256(b"gallery-k-dummy").digest()),
    bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
)


def _prepare(password: str) -> bytes:
    """bcrypt는 72바이트까지만 본다.

    비밀번호 상한이 64**자**이므로 한글이면 192바이트가 되어 조용히 잘린다. sha256으로
    한 번 접어 길이를 고정하면 상한 안의 모든 문자가 해시에 기여한다.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    """해시가 없어도(=미가입) 같은 비용을 치른다."""
    if not password_hash:
        bcrypt.checkpw(_prepare(password), _DUMMY_HASH)
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("ascii"))
    except ValueError:
        # 손상된 해시. 존재를 드러내지 않고 실패로 처리한다.
        bcrypt.checkpw(_prepare(password), _DUMMY_HASH)
        return False


# ── 세션 토큰 ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SessionClaims:
    user_id: uuid.UUID
    role: str
    token_version: int
    issued_at: _dt.datetime
    expires_at: _dt.datetime
    jti: str

    @property
    def needs_renewal(self) -> bool:
        """만료 30일 이내면 응답에서 자동 재발급한다 (슬라이딩 세션)."""
        remaining = (self.expires_at - now_utc()).total_seconds()
        return remaining <= SESSION_SLIDING_RENEW_WITHIN_SECONDS


def issue_session_token(
    *,
    user_id: uuid.UUID,
    role: str,
    token_version: int,
    issued_at: _dt.datetime,
    ttl_seconds: int = SESSION_COOKIE_MAX_AGE_SECONDS,
) -> tuple[str, _dt.datetime]:
    """세션 수명은 운영 중 조정되는 값이다(`app_setting.session_ttl_days`, DB 문서 §4.9).

    기본값은 문서가 못박은 90일이며, 설정을 읽지 못하는 상황에서도 그 값으로 발급된다.
    """
    expires_at = issued_at + _dt.timedelta(seconds=ttl_seconds)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": new_request_id(),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_session_token(token: str) -> SessionClaims:
    """만료·위조를 구분해 던진다. 둘 다 401이지만 코드가 다르다(§5.2)."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.AUTH_SESSION_EXPIRED) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(ErrorCode.AUTH_REQUIRED, doc_hint="세션 토큰을 해석할 수 없습니다") from exc

    try:
        return SessionClaims(
            user_id=uuid.UUID(payload["sub"]),
            role=str(payload["role"]),
            token_version=int(payload["tv"]),
            issued_at=_dt.datetime.fromtimestamp(int(payload["iat"]), tz=_dt.UTC),
            expires_at=_dt.datetime.fromtimestamp(int(payload["exp"]), tz=_dt.UTC),
            jti=str(payload.get("jti", "")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise AppError(ErrorCode.AUTH_REQUIRED, doc_hint="세션 토큰의 클레임이 올바르지 않습니다") from exc


# ── 쿠키 ───────────────────────────────────────────────────────────────────


def build_session_cookie(token: str, *, max_age_seconds: int = SESSION_COOKIE_MAX_AGE_SECONDS) -> str:
    attributes = [
        f"{SESSION_COOKIE_NAME}={token}",
        f"Path={SESSION_COOKIE_PATH}",
        f"Max-Age={max_age_seconds}",
        f"SameSite={SESSION_COOKIE_SAMESITE}",
        "HttpOnly",
    ]
    # 로컬 http 개발에서 Secure를 붙이면 브라우저가 쿠키를 버린다.
    if settings.is_production:
        attributes.append("Secure")
    return "; ".join(attributes)


def _cookie(name: str, value: str, *, max_age_seconds: int) -> str:
    attributes = [
        f"{name}={value}",
        f"Path={SESSION_COOKIE_PATH}",
        f"Max-Age={max_age_seconds}",
        # `Lax`가 소셜 리다이렉트를 견딘다 — 제공자에서 돌아오는 길은 top-level GET
        # 내비게이션이라 쿠키가 함께 간다(소셜 문서 §2). 팝업·iframe이었다면
        # `SameSite=None`으로 내려야 했고 그 순간 CSRF 방어 한 겹이 사라진다.
        f"SameSite={SESSION_COOKIE_SAMESITE}",
        "HttpOnly",
    ]
    # 로컬 http 개발에서 Secure를 붙이면 브라우저가 쿠키를 버린다.
    if settings.is_production:
        attributes.append("Secure")
    return "; ".join(attributes)


def build_expired_session_cookie() -> str:
    attributes = [
        f"{SESSION_COOKIE_NAME}=",
        f"Path={SESSION_COOKIE_PATH}",
        "Max-Age=0",
        f"SameSite={SESSION_COOKIE_SAMESITE}",
        "HttpOnly",
    ]
    if settings.is_production:
        attributes.append("Secure")
    return "; ".join(attributes)


def read_cookie(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    for chunk in cookie_header.split(";"):
        key, _, value = chunk.strip().partition("=")
        if key == name:
            return value or None
    return None


# ── 소셜 로그인 임시 쿠키 (소셜 문서 §4) ───────────────────────────────────
#
# `state`·`code_verifier`·`nonce`를 DB가 아니라 **서명 쿠키**에 둔다. Lambda는 인스턴스
# 메모리를 신뢰할 수 없고(백엔드 문서 §4), 이 값들은 10분 뒤 무의미해진다. DB에 두면
# 만료 행을 지우는 정리 작업이 하나 더 생긴다. 서명 쿠키는 만료가 곧 소멸이다.

#: 임시 쿠키 JWT의 용도 구분. 인가 왕복 티켓을 연결 티켓으로 쓰는 혼선을 막는다.
_PURPOSE_OAUTH: Final = "oauth_state"
_PURPOSE_LINK: Final = "oauth_link"


def new_state_secret() -> str:
    """`state`·`nonce`·`code_verifier`의 원천. URL-safe 43자(256비트)."""
    return secrets.token_urlsafe(32)


def code_challenge_of(code_verifier: str) -> str:
    """PKCE S256 (RFC 7636 §4.2). `plain`은 쓰지 않는다 — 그러면 PKCE가 무의미하다."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _encode_ticket(payload: dict[str, Any], *, purpose: str, ttl_seconds: int) -> str:
    now = now_utc()
    claims = {
        **payload,
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int((now + _dt.timedelta(seconds=ttl_seconds)).timestamp()),
        "jti": new_request_id(),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_ticket(token: str, *, purpose: str) -> dict[str, Any] | None:
    """만료·위조·용도 불일치를 **모두 `None`으로** 접는다.

    호출부가 사유별로 분기할 이유가 없다 — 셋 다 "처음부터 다시 하세요"로 끝난다.
    """
    try:
        claims: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        return None
    if claims.get("purpose") != purpose:
        return None
    return claims


@dataclass(frozen=True, slots=True)
class OAuthTicket:
    """인가 왕복 동안 서버가 기억해야 하는 것 전부."""

    provider: str
    state: str
    code_verifier: str
    nonce: str
    next_path: str


def build_oauth_state_cookie(ticket: OAuthTicket, *, ttl_seconds: int) -> str:
    token = _encode_ticket(
        {
            "provider": ticket.provider,
            "state": ticket.state,
            "verifier": ticket.code_verifier,
            "nonce": ticket.nonce,
            "next": ticket.next_path,
        },
        purpose=_PURPOSE_OAUTH,
        ttl_seconds=ttl_seconds,
    )
    return _cookie(OAUTH_STATE_COOKIE_NAME, token, max_age_seconds=ttl_seconds)


def read_oauth_state_ticket(token: str | None) -> OAuthTicket | None:
    if not token:
        return None
    claims = _decode_ticket(token, purpose=_PURPOSE_OAUTH)
    if claims is None:
        return None
    try:
        return OAuthTicket(
            provider=str(claims["provider"]),
            state=str(claims["state"]),
            code_verifier=str(claims["verifier"]),
            nonce=str(claims["nonce"]),
            next_path=str(claims["next"]),
        )
    except KeyError:
        return None


@dataclass(frozen=True, slots=True)
class LinkTicket:
    """A-4 화면이 들고 있는 것.

    **어떤 계정에 연결할지는 담지 않는다.** 그것은 전화번호와 비밀번호로 증명한다 —
    티켓만 훔쳐서는 아무 계정도 가져갈 수 없다(소셜 문서 §4).
    """

    provider: str
    provider_uid: str
    email: str | None
    display_name: str | None
    next_path: str


def build_oauth_link_cookie(ticket: LinkTicket, *, ttl_seconds: int) -> str:
    token = _encode_ticket(
        {
            "provider": ticket.provider,
            "uid": ticket.provider_uid,
            "email": ticket.email,
            "display_name": ticket.display_name,
            "next": ticket.next_path,
        },
        purpose=_PURPOSE_LINK,
        ttl_seconds=ttl_seconds,
    )
    return _cookie(OAUTH_LINK_COOKIE_NAME, token, max_age_seconds=ttl_seconds)


def read_oauth_link_ticket(token: str | None) -> LinkTicket | None:
    if not token:
        return None
    claims = _decode_ticket(token, purpose=_PURPOSE_LINK)
    if claims is None:
        return None
    try:
        return LinkTicket(
            provider=str(claims["provider"]),
            provider_uid=str(claims["uid"]),
            email=claims.get("email"),
            display_name=claims.get("display_name"),
            next_path=str(claims.get("next") or "/gallery"),
        )
    except KeyError:
        return None


def build_expired_cookie(name: str) -> str:
    """임시 쿠키는 **쓰는 즉시 지운다.** 재사용이 곧 리플레이다."""
    attributes = [
        f"{name}=",
        f"Path={SESSION_COOKIE_PATH}",
        "Max-Age=0",
        f"SameSite={SESSION_COOKIE_SAMESITE}",
        "HttpOnly",
    ]
    if settings.is_production:
        attributes.append("Secure")
    return "; ".join(attributes)

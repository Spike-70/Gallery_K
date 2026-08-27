"""인증 원시 연산 (백엔드 문서 §13, API 문서 §2.7).

* 비밀번호는 bcrypt. **실패 경로도 동일한 시간이 걸리게 한다** — 미가입 번호와
  비밀번호 불일치의 응답 시간이 다르면 계정 존재 여부가 새어 나간다(§5.2).
* 세션 토큰은 JWT(HS256)이며 **HttpOnly 쿠키로만** 전달한다. 응답 바디에 넣지 않는다.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Final

import bcrypt
import jwt

from chalicelib.config.constants import (
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

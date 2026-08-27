"""가입·로그인·비밀번호 (API 문서 §6, PRD §6.2·§6.4).

**존재를 숨기는 규칙** — 미가입·차단·오답 로그인은 모두 같은 응답을 준다. 어느 하나라도
다르게 답하면 전화번호부를 가진 사람이 회원 명단을 복원할 수 있다.

실패 경로도 성공 경로와 같은 시간이 걸리게 한다(`verify_password`가 해시가 없어도 같은
비용을 치른다).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from chalicelib.config.constants import PASSWORD_MIN_LENGTH
from chalicelib.core.errors import AppError, ErrorCode
from chalicelib.core.logging import get_logger, log_event
from chalicelib.core.security import hash_password, verify_password
from chalicelib.core.timeutil import now_utc, parse_time_of_day
from chalicelib.db import query as q
from chalicelib.db.models import AppUser
from chalicelib.db.models.enums import CreatedVia, ThrottleScope, UserRole
from chalicelib.services import (
    member_service,
    notification_service,
    session_service,
    setting_service,
    throttle_service,
)
from chalicelib.services.setting_service import SettingKey
from chalicelib.utils.text import normalize_phone

logger = get_logger("auth")

#: 가입 경로 별칭. `api` 계층은 `db.models`를 직접 import 하지 않는다(문서 §5).
VIA_SELF: Final = CreatedVia.SELF
VIA_CURATOR: Final = CreatedVia.CURATOR


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """로그인 결과. 쿠키 발급에 필요한 값과 응답 DTO를 함께 담는다."""

    id: uuid.UUID
    role: str
    token_version: int
    user: dict[str, Any]


def _guard_password_policy(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AppError(ErrorCode.PASSWORD_POLICY_VIOLATION, details={"min_length": PASSWORD_MIN_LENGTH})


def signup(
    session: Session, *, phone: str, password: str, name: str, created_via: str = CreatedVia.SELF
) -> AuthenticatedUser:
    """가입 성공 시 **자동 로그인**되어 C 갤러리로 직행한다 (PRD §6.4)."""
    normalized = normalize_phone(phone)
    _guard_password_policy(password)

    # 가입 잠금은 외부 가입을 막는 장치이지 큐레이터를 막는 장치가 아니다(API 문서 §9.14).
    if created_via == CreatedVia.SELF and not setting_service.get_bool(session, SettingKey.SIGNUP_OPEN):
        raise AppError(ErrorCode.SIGNUP_CLOSED)

    if q.exists(session, AppUser, where={"phone": normalized}):
        raise AppError(ErrorCode.SIGNUP_PHONE_TAKEN)

    default_time = parse_time_of_day(setting_service.get_str(session, SettingKey.NOTIFY_DEFAULT_TIME))
    now = now_utc()
    user = q.insert(
        session,
        AppUser,
        {
            "phone": normalized,
            "password_hash": hash_password(password),
            "name": name,
            "role": UserRole.VIEWER,
            "created_via": created_via,
            # 큐레이터가 대신 만든 계정은 첫 로그인에서 비밀번호를 바꾼다.
            "must_change_password": created_via == CreatedVia.CURATOR,
            "notify_enabled": True,
            "notify_at": default_time,
            "last_login_at": now if created_via == CreatedVia.SELF else None,
        },
    )
    notification_service.queue_curator_signup(session, new_user_id=user.id, new_user_name=user.name)
    log_event(logger, "auth.signup", created_via=created_via)

    return AuthenticatedUser(
        id=user.id,
        role=user.role,
        token_version=user.token_version,
        user=member_service.serialize_session_user(user),
    )


def login(session: Session, *, phone: str, password: str) -> AuthenticatedUser:
    """미가입·비밀번호 불일치·차단 회원을 **구분하지 않는다** (API 문서 §5.2)."""
    normalized = normalize_phone(phone)
    user = q.fetch_one(session, AppUser, where={"phone": normalized})

    password_ok = verify_password(password, user.password_hash if user else None)
    blocked = bool(user and user.is_blocked)

    if user is None or not password_ok or blocked:
        retry_after = throttle_service.register_hit(ThrottleScope.LOGIN, normalized)
        log_event(
            logger,
            "auth.login.failed",
            # 어느 사유인지는 로그에만 남는다. 응답은 세 경우 모두 같다.
            reason="not_found" if user is None else ("blocked" if blocked else "bad_password"),
        )
        if retry_after > 0:
            raise AppError(ErrorCode.AUTH_TOO_MANY_ATTEMPTS, details={"retry_after_seconds": retry_after})
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS)

    throttle_service.clear(ThrottleScope.LOGIN, normalized)
    q.update(session, AppUser, where={"id": user.id}, values={"last_login_at": now_utc()})
    session.refresh(user)
    log_event(logger, "auth.login.succeeded")

    return AuthenticatedUser(
        id=user.id,
        role=user.role,
        token_version=user.token_version,
        user=member_service.serialize_session_user(user),
    )


def change_password(
    session: Session, user_id: uuid.UUID, *, current_password: str, new_password: str
) -> AuthenticatedUser:
    """`token_version`이 증가하므로 다른 단말 세션은 무효화된다 (API 문서 §6.7).

    `must_change_password=true`인 사용자는 현재 비밀번호에 초기 비밀번호를 넣어 해소한다.
    """
    user = member_service.get_user(session, user_id)
    if not verify_password(current_password, user.password_hash):
        raise AppError(ErrorCode.PASSWORD_CURRENT_MISMATCH)
    _guard_password_policy(new_password)

    q.update(
        session,
        AppUser,
        where={"id": user_id},
        values={
            "password_hash": hash_password(new_password),
            "must_change_password": False,
            **session_service.revocation_values(),
        },
    )
    session.refresh(user)
    log_event(logger, "auth.password.changed")

    return AuthenticatedUser(
        id=user.id,
        role=user.role,
        token_version=user.token_version,
        user=member_service.serialize_session_user(user),
    )


def request_password_reset(session: Session, *, phone: str) -> None:
    """v1.1 — SMS 인증번호 발송 (API 문서 §6.8).

    **미가입 번호에도 동일한 성공 응답을 반환하며 실제로는 발송하지 않는다.**
    경로와 스키마는 MVP 시점에 확정하되 발송 어댑터는 v1.1에서 붙인다.
    """
    normalized = normalize_phone(phone)
    exists = q.exists(session, AppUser, where={"phone": normalized})
    log_event(logger, "auth.password_reset.requested", delivered=False, known=exists)


def confirm_password_reset(session: Session, *, phone: str, code: str, new_password: str) -> None:
    """v1.1 — 인증번호 확인 후 새 비밀번호 (API 문서 §6.9).

    발송 수단이 없는 동안에는 어떤 코드도 유효하지 않다. 코드 저장 테이블은 SMS 어댑터와
    함께 들어온다(DB 문서 §11 확장 훅).
    """
    _guard_password_policy(new_password)
    raise AppError(ErrorCode.RESET_CODE_INVALID, details={"attempts_left": 0})

"""인증·계정 요청/응답 스키마 (API 문서 §6)."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from chalicelib.config.constants import (
    LIMIT_MEMBER_NAME,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PHONE_PATTERN,
)
from chalicelib.schemas.common import STRICT

_PHONE_RE = re.compile(PHONE_PATTERN)

Password = Annotated[str, Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)]
MemberName = Annotated[str, Field(min_length=1, max_length=LIMIT_MEMBER_NAME)]


class PhoneMixin(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """하이픈은 화면의 편의이고 저장·검증은 숫자만 본다 (API 문서 §6.3)."""
        from chalicelib.utils.text import normalize_phone

        digits = normalize_phone(value)
        if not _PHONE_RE.fullmatch(digits):
            raise ValueError("전화번호 형식이 올바르지 않습니다.")
        return digits


class SignupIn(PhoneMixin):
    model_config = STRICT

    password: Password
    name: MemberName
    #: 이용·개인정보 처리 동의 1건. 비상업 서비스이므로 항목을 최소화한다(PRD §6.4).
    agreed_terms: Literal[True]


class LoginIn(PhoneMixin):
    model_config = STRICT

    # 로그인은 정책 길이를 강제하지 않는다 — 정책 이전에 만들어진 비밀번호도 들어와야 하고,
    # 길이로 존재 여부를 흘리지 않기 위해서다.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class PasswordChangeIn(BaseModel):
    model_config = STRICT

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: Password


class PasswordResetRequestIn(PhoneMixin):
    model_config = STRICT


class PasswordResetConfirmIn(PhoneMixin):
    model_config = STRICT

    code: str = Field(pattern=r"^\d{6}$")
    new_password: Password


class SessionUserOut(BaseModel):
    """§3.6 — `phone_masked`만 나간다. 전체 번호는 관리자 응답 전용이다."""

    id: str
    name: str
    phone_masked: str
    role: Literal["viewer", "curator"]
    font_scale: Literal["normal", "large"]
    notify_enabled: bool
    notify_at: str
    must_change_password: bool
    #: false면 소셜로만 로그인하는 계정이다. D 설정이 비밀번호 변경 항목을 감춘다.
    has_password: bool
    created_at: str


class SessionOut(BaseModel):
    """§6.6 — 비로그인이어도 200이다."""

    is_authenticated: bool
    user: SessionUserOut | None


class UserOut(BaseModel):
    user: SessionUserOut


class SignupOut(BaseModel):
    user: SessionUserOut
    is_first_login: Literal[True]


class PasswordResetRequestOut(BaseModel):
    expires_in_seconds: int
    resend_after_seconds: int


# ── 소셜 로그인 (API 문서 §6.11–§6.15) ─────────────────────────────────────


class SocialLinkIn(PhoneMixin):
    """A-4 `이미 회원이신가요?` — 비밀번호로 계정 소유를 증명한다(소셜 문서 §4).

    로그인과 같은 이유로 길이 정책을 강제하지 않는다 — 정책 이전에 만들어진
    비밀번호도 들어와야 하고, 길이로 존재 여부를 흘리지 않기 위해서다.
    """

    model_config = STRICT

    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class SocialSignupIn(PhoneMixin):
    """A-4 `처음이신가요?` — 비밀번호를 받지 않는다. 소셜이 곧 로그인 수단이다."""

    model_config = STRICT

    name: MemberName
    agreed_terms: Literal[True]


class SocialProviderOut(BaseModel):
    provider: Literal["kakao", "google"]
    label: str
    start_url: str


class SocialProvidersOut(BaseModel):
    providers: list[SocialProviderOut]


class SocialIdentityOut(BaseModel):
    """§3.10 — **제공자 토큰은 담기지 않는다**(소셜 문서 SA-3)."""

    id: str
    provider: Literal["kakao", "google"]
    label: str
    email: str | None
    display_name: str | None
    linked_at: str
    last_login_at: str | None


class SocialIdentitiesOut(BaseModel):
    identities: list[SocialIdentityOut]
    #: false면 화면이 해제 버튼을 잠근다. 마지막 로그인 수단이기 때문이다(SA-6).
    can_unlink: bool

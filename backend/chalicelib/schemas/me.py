"""회원 API 스키마 (API 문서 §8)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from chalicelib.config.constants import NOTIFY_AT_MAX, NOTIFY_AT_MIN
from chalicelib.schemas.common import STRICT


class SettingsPatchIn(BaseModel):
    """부분 갱신. **보낸 필드만** 반영한다."""

    model_config = STRICT

    notify_enabled: bool | None = None
    notify_at: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    font_scale: Literal["normal", "large"] | None = None

    @model_validator(mode="after")
    def _reject_empty(self) -> SettingsPatchIn:
        """빈 바디는 거부한다 — 의도 없는 PATCH는 버그 신호다 (API 문서 §8.2)."""
        if self.notify_enabled is None and self.notify_at is None and self.font_scale is None:
            raise ValueError("변경할 항목이 없습니다.")
        return self

    @model_validator(mode="after")
    def _check_notify_range(self) -> SettingsPatchIn:
        """05:00–11:00. 아침 알림이 아닌 시각을 고를 수 있으면 그 자체가 사고다."""
        if self.notify_at is not None and not (NOTIFY_AT_MIN <= self.notify_at <= NOTIFY_AT_MAX):
            raise ValueError(f"알림 시각은 {NOTIFY_AT_MIN}부터 {NOTIFY_AT_MAX} 사이여야 합니다.")
        return self


class WithdrawIn(BaseModel):
    """실수 방지를 위해 명시적 확인 필드를 요구한다."""

    model_config = STRICT

    confirm: Literal[True]


class PushKeysIn(BaseModel):
    model_config = STRICT

    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionIn(BaseModel):
    model_config = STRICT

    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushKeysIn
    platform: Literal["ios", "android", "desktop", "unknown"] | None = None


class PushSubscriptionOut(BaseModel):
    """§8.5 — `endpoint` 원문은 반환하지 않는다."""

    id: str
    endpoint_hash: str
    platform: str
    is_active: bool
    created_at: str
    last_success_at: str | None


class PushSubscriptionsOut(BaseModel):
    subscriptions: list[PushSubscriptionOut]


class PushSubscribeOut(BaseModel):
    subscription_id: str
    is_new: bool

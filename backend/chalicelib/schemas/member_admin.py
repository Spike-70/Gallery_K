"""회원 관리·설정·공지·통계 스키마 (API 문서 §9.13–§9.19)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from chalicelib.config.constants import (
    LIMIT_BLOCKED_REASON,
    LIMIT_NOTICE_BODY,
    LIMIT_SEARCH_QUERY,
)
from chalicelib.schemas.auth import MemberName, Password, PhoneMixin
from chalicelib.schemas.common import STRICT, NoticeItemOut

MemberSort = Literal["created_at", "-created_at", "name", "-name", "last_viewed_on", "-last_viewed_on"]


# ── 회원 ───────────────────────────────────────────────────────────────────


class MemberListQuery(BaseModel):
    model_config = STRICT

    query: str | None = Field(default=None, min_length=1, max_length=LIMIT_SEARCH_QUERY)
    status: Literal["all", "active", "blocked"] = "all"
    notify: Literal["all", "on", "off"] = "all"
    sort: MemberSort = "-created_at"


class MemberCreateIn(PhoneMixin):
    """대행 가입 — 가입 잠금 상태에서도 생성 가능하다 (API 문서 §9.14)."""

    model_config = STRICT

    name: MemberName
    initial_password: Password


class BlockIn(BaseModel):
    model_config = STRICT

    reason: str | None = Field(default=None, max_length=LIMIT_BLOCKED_REASON)


class ResetPasswordIn(BaseModel):
    model_config = STRICT

    new_password: Password


class MemberItemOut(BaseModel):
    """§3.8 — 관리자 응답에서만 전체 번호를 반환한다."""

    id: str
    name: str
    phone: str
    role: Literal["viewer", "curator"]
    created_at: str
    created_via: Literal["self", "curator"]
    is_blocked: bool
    blocked_at: str | None
    notify_enabled: bool
    notify_at: str
    push_status: Literal["active", "inactive", "none"]
    push_platforms: list[str]
    last_login_at: str | None
    last_viewed_on: str | None


class MemberListOut(BaseModel):
    members: list[MemberItemOut]
    #: B-3 상단 스위치가 별도 요청 없이 렌더된다.
    signup_open: bool


class MemberOut(BaseModel):
    member: MemberItemOut


# ── 설정 ───────────────────────────────────────────────────────────────────


class AppSettingsPatchIn(BaseModel):
    """전역 설정 변경. 회원 개인 설정(`schemas/me.py`)과 이름이 겹치지 않게 한다."""

    model_config = STRICT

    settings: dict[str, Any] = Field(min_length=1)


class AppSettingOut(BaseModel):
    key: str
    value: Any
    value_type: Literal["string", "number", "boolean"]
    description: str
    is_mutable: bool
    updated_at: str | None


class SettingsOut(BaseModel):
    settings: list[AppSettingOut]


# ── 공지 ───────────────────────────────────────────────────────────────────


class NoticeListQuery(BaseModel):
    model_config = STRICT

    include_past: bool = False


class NoticeCreateIn(BaseModel):
    model_config = STRICT

    starts_on: str
    ends_on: str
    body: str = Field(min_length=1, max_length=LIMIT_NOTICE_BODY)


class NoticePatchIn(BaseModel):
    model_config = STRICT

    starts_on: str | None = None
    ends_on: str | None = None
    body: str | None = Field(default=None, min_length=1, max_length=LIMIT_NOTICE_BODY)


class NoticeListOut(BaseModel):
    notices: list[NoticeItemOut]


class NoticeOut(BaseModel):
    notice: NoticeItemOut


# ── 통계 (v1.1) ────────────────────────────────────────────────────────────


class StatsRangeQuery(BaseModel):
    model_config = STRICT

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None


class StatsMemberSearchQuery(BaseModel):
    model_config = STRICT

    query: str = Field(min_length=1, max_length=LIMIT_SEARCH_QUERY)


class StatsMemberDetailQuery(BaseModel):
    model_config = STRICT

    days: int | None = None


class StatsDayOut(BaseModel):
    date: str
    exhibition_date: str | None
    exhibition_title: str | None
    is_carried_over: bool
    entrant_count: int
    artwork_view_count: int


class StatsDailyOut(BaseModel):
    days: list[StatsDayOut]


class StatsMemberCandidateOut(BaseModel):
    id: str
    name: str
    phone_masked: str
    last_viewed_on: str | None


class StatsMembersOut(BaseModel):
    members: list[StatsMemberCandidateOut]


class MemberStatsDayOut(BaseModel):
    date: str
    exhibition_date: str | None
    exhibition_title: str | None
    entered: bool
    viewed_artwork_count: int
    total_artwork_count: int


class StatsMemberDetailOut(BaseModel):
    member: dict[str, str]
    days: list[MemberStatsDayOut]

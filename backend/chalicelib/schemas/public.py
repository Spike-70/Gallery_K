"""공개 API 스키마 (API 문서 §6.1·§6.2·§10.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from chalicelib.schemas.common import NoticeItemOut


class LandingOut(BaseModel):
    """§6.1 — A 첫 화면이 필요로 하는 모든 것."""

    today: str
    today_label: str
    exhibition_title: str | None
    has_exhibition: bool
    notice: NoticeItemOut | None
    signup_open: bool
    is_authenticated: bool
    is_curator: bool
    member_name: str | None


class NoticeOut(BaseModel):
    """§6.2 — 공지만 확인하는 경량 폴링 경로."""

    notice: NoticeItemOut | None


class HealthChecks(BaseModel):
    database: Literal["ok", "fail"]
    storage: Literal["ok", "fail"]


class HealthOut(BaseModel):
    """§10.1 — `degraded`여도 HTTP 200이다."""

    status: Literal["ok", "degraded"]
    checks: HealthChecks
    version: str

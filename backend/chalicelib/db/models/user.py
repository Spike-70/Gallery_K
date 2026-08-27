"""회원과 인증 부수 테이블 (DB 문서 §4.1–§4.3)."""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import text as sa_text
from sqlmodel import Field, SQLModel

from chalicelib.config.constants import PHONE_PATTERN
from chalicelib.db.models.base import TimestampMixin, UUIDPKMixin
from chalicelib.db.models.enums import CreatedVia, FontScale, PushPlatform, ThrottleScope, UserRole, values


def _in_check(column: str, allowed: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{value}'" for value in allowed)
    return f"{column} IN ({joined})"


class AppUser(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """관람자·큐레이터를 `role`로 구분하는 단일 테이블.

    차단은 기존 세션을 끊지 않는다 — 로그인 시점에만 작동한다(PRD §6.4).
    즉시 차단이 필요해지면 `token_version` 증가로 열린다(DB 문서 §11).
    """

    __tablename__ = "app_user"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_app_user_phone"),
        CheckConstraint(f"phone ~ '{PHONE_PATTERN}'", name="phone_format"),
        CheckConstraint(_in_check("role", values(UserRole)), name="role"),
        CheckConstraint(_in_check("font_scale", values(FontScale)), name="font_scale"),
        CheckConstraint(_in_check("created_via", values(CreatedVia)), name="created_via"),
        CheckConstraint("token_version >= 0", name="token_version"),
        CheckConstraint(
            "(is_blocked AND blocked_at IS NOT NULL) OR (NOT is_blocked AND blocked_at IS NULL)",
            name="blocked_consistency",
        ),
        # 큐레이터는 시드로 1건만 생성한다. 다중 큐레이터는 이 부분 유니크 제거만으로 열린다.
        Index(
            "uq_app_user_single_curator",
            "role",
            unique=True,
            postgresql_where=sa_text("role = 'curator'"),
        ),
        # 알림 대상 조회용. 스케줄러가 매 주기 타는 유일한 경로다.
        Index(
            "ix_app_user_notify_target",
            "notify_at",
            postgresql_where=sa_text("notify_enabled AND NOT is_blocked"),
        ),
        Index("ix_app_user_created_at", sa_text("created_at DESC")),
        # 이름 부분 검색(B-3 회원 목록). LIKE '%…%'는 B-tree를 타지 못한다.
        Index(
            "ix_app_user_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    # 신원·인증
    phone: str = Field(sa_column=Column("phone", String(11), nullable=False))
    password_hash: str = Field(sa_column=Column("password_hash", String(72), nullable=False))
    name: str = Field(sa_column=Column("name", String(20), nullable=False))
    role: str = Field(
        default=UserRole.VIEWER,
        sa_column=Column("role", String(10), nullable=False, server_default=sa_text("'viewer'")),
    )
    #: JWT 무효화 카운터. 클레임 `tv`와 다르면 즉시 거부한다.
    token_version: int = Field(
        default=0,
        sa_column=Column("token_version", Integer, nullable=False, server_default=sa_text("0")),
    )
    must_change_password: bool = Field(
        default=False,
        sa_column=Column("must_change_password", Boolean, nullable=False, server_default=sa_text("false")),
    )
    last_login_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("last_login_at", DateTime(timezone=True), nullable=True)
    )

    # 설정 — 알림을 꺼도 시각 값은 보존한다(다시 켤 때 그대로 쓰기 위함)
    notify_enabled: bool = Field(
        default=True,
        sa_column=Column("notify_enabled", Boolean, nullable=False, server_default=sa_text("true")),
    )
    notify_at: _dt.time = Field(
        default=_dt.time(7, 30),
        sa_column=Column(
            "notify_at", Time(timezone=False), nullable=False, server_default=sa_text("'07:30'")
        ),
    )
    font_scale: str = Field(
        default=FontScale.NORMAL,
        sa_column=Column("font_scale", String(10), nullable=False, server_default=sa_text("'normal'")),
    )

    # 운영
    is_blocked: bool = Field(
        default=False,
        sa_column=Column("is_blocked", Boolean, nullable=False, server_default=sa_text("false")),
    )
    blocked_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("blocked_at", DateTime(timezone=True), nullable=True)
    )
    blocked_reason: str | None = Field(
        default=None, sa_column=Column("blocked_reason", String(200), nullable=True)
    )
    created_via: str = Field(
        default=CreatedVia.SELF,
        sa_column=Column("created_via", String(10), nullable=False, server_default=sa_text("'self'")),
    )


class AuthThrottle(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """인증 시도 제한 (DB 문서 §4.2).

    Lambda는 인스턴스 메모리를 신뢰할 수 없으므로 시도 상태를 DB에 둔다.
    실패는 UPSERT로 원자적 증가, 성공 시 행 삭제.
    """

    __tablename__ = "auth_throttle"
    __table_args__ = (
        UniqueConstraint("throttle_key", name="uq_auth_throttle_throttle_key"),
        CheckConstraint(_in_check("scope", values(ThrottleScope)), name="scope"),
        CheckConstraint("fail_count >= 0", name="fail_count"),
        Index("ix_auth_throttle_locked_until", "locked_until"),
    )

    #: `{scope}:{식별자}` — 식별자는 전화번호이거나 IP다.
    throttle_key: str = Field(sa_column=Column("throttle_key", String(120), nullable=False))
    scope: str = Field(sa_column=Column("scope", String(20), nullable=False))
    fail_count: int = Field(
        default=0, sa_column=Column("fail_count", Integer, nullable=False, server_default=sa_text("0"))
    )
    first_failed_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("first_failed_at", DateTime(timezone=True), nullable=True)
    )
    last_failed_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("last_failed_at", DateTime(timezone=True), nullable=True)
    )
    locked_until: _dt.datetime | None = Field(
        default=None, sa_column=Column("locked_until", DateTime(timezone=True), nullable=True)
    )


class PushSubscription(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """웹 푸시 구독 (DB 문서 §4.3). 한 회원이 여러 단말을 구독할 수 있어 1:N.

    같은 엔드포인트가 다른 회원으로 재등록되면 소유자를 갱신한다 — 가족이 한 기기를
    공유하는 경우가 실제로 있다.
    """

    __tablename__ = "push_subscription"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_push_subscription_endpoint_hash"),
        CheckConstraint(_in_check("platform", values(PushPlatform)), name="platform"),
        CheckConstraint("failure_count >= 0", name="failure_count"),
        Index(
            "ix_push_subscription_user_active",
            "user_id",
            postgresql_where=sa_text("is_active"),
        ),
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            Uuid,
            ForeignKey("app_user.id", ondelete="CASCADE", name="fk_push_subscription_user_id"),
            nullable=False,
        )
    )
    endpoint: str = Field(sa_column=Column("endpoint", String(2048), nullable=False))
    #: 엔드포인트 원문은 인덱스 상한을 넘길 수 있어 해시로 유일성을 건다.
    endpoint_hash: str = Field(sa_column=Column("endpoint_hash", String(64), nullable=False))
    p256dh: str = Field(sa_column=Column("p256dh", String(255), nullable=False))
    auth: str = Field(sa_column=Column("auth", String(255), nullable=False))
    platform: str = Field(
        default=PushPlatform.UNKNOWN,
        sa_column=Column("platform", String(10), nullable=False, server_default=sa_text("'unknown'")),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column("is_active", Boolean, nullable=False, server_default=sa_text("true")),
    )
    failure_count: int = Field(
        default=0,
        sa_column=Column("failure_count", Integer, nullable=False, server_default=sa_text("0")),
    )
    last_success_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("last_success_at", DateTime(timezone=True), nullable=True)
    )
    deactivated_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("deactivated_at", DateTime(timezone=True), nullable=True)
    )

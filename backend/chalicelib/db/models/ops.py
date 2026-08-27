"""운영 테이블 — 공지·전역 설정·알림 이력·감사 이력 (DB 문서 §4.8–§4.11)."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlmodel import Field, SQLModel

from chalicelib.config.constants import LIMIT_NOTICE_BODY
from chalicelib.db.models.base import TimestampMixin, UUIDPKMixin
from chalicelib.db.models.enums import NotificationKind, NotificationStatus, values


class Notice(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """휴관 공지 (DB 문서 §4.8).

    활성 공지의 기간 중첩을 EXCLUDE로 금지한다. 겹침을 허용하면 "오늘의 공지"가
    비결정적이 된다 — 두 개가 유효한 날 무엇을 보여줄지 코드가 정하게 된다.
    """

    __tablename__ = "notice"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="period_order"),
        ExcludeConstraint(
            (sa_text("daterange(starts_on, ends_on, '[]')"), "&&"),
            name="ex_notice_active_period",
            using="gist",
            where=sa_text("is_active"),
        ),
        Index("ix_notice_period", "starts_on", "ends_on", postgresql_where=sa_text("is_active")),
    )

    starts_on: _dt.date = Field(sa_column=Column("starts_on", Date, nullable=False))
    ends_on: _dt.date = Field(sa_column=Column("ends_on", Date, nullable=False))
    body: str = Field(sa_column=Column("body", String(LIMIT_NOTICE_BODY), nullable=False))
    #: 취소는 삭제가 아니라 비활성이다 — 무엇을 언제 걸었는지가 남는다.
    is_active: bool = Field(
        default=True,
        sa_column=Column("is_active", Boolean, nullable=False, server_default=sa_text("true")),
    )
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "created_by",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_notice_created_by"),
            nullable=True,
        ),
    )


class AppSetting(TimestampMixin, SQLModel, table=True):
    """전역 설정 (DB 문서 §4.9). 키-값 단일 테이블이며 설정마다 컬럼을 늘리지 않는다.

    **배포로만 바뀌는 값은 환경변수, 운영 중 조정되는 값은 이 테이블**이다.
    """

    __tablename__ = "app_setting"
    __table_args__ = (CheckConstraint("value_type IN ('string', 'number', 'boolean')", name="value_type"),)

    key: str = Field(sa_column=Column("key", String(60), primary_key=True, nullable=False))
    value: Any = Field(sa_column=Column("value", JSONB, nullable=False))
    value_type: str = Field(sa_column=Column("value_type", String(10), nullable=False))
    description: str = Field(
        default="", sa_column=Column("description", String(200), nullable=False, server_default=sa_text("''"))
    )
    #: 잠긴 설정은 API로 바뀌지 않는다. 배포로만 바꾼다.
    is_mutable: bool = Field(
        default=True,
        sa_column=Column("is_mutable", Boolean, nullable=False, server_default=sa_text("true")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "updated_by",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_app_setting_updated_by"),
            nullable=True,
        ),
    )


class NotificationLog(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """알림 발송 이력 (DB 문서 §4.10).

    `dedupe_key` UNIQUE가 "하루 1회"와 "연장 기간당 1회"를 **DB 수준에서** 보장한다.
    스케줄러 중복 기동이 무해해지는 근거가 이 제약 하나다.

    발송하지 않기로 한 경우에도 `skipped` 행을 남긴다 — 보내지 않은 이유가 남아야
    문의에 답할 수 있다.
    """

    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notification_log_dedupe_key"),
        CheckConstraint(f"kind IN ({', '.join(repr(v) for v in values(NotificationKind))})", name="kind"),
        CheckConstraint(
            f"status IN ({', '.join(repr(v) for v in values(NotificationStatus))})", name="status"
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count"),
        # 스케줄러가 매 주기 타는 경로. 대기 행만 본다.
        Index(
            "ix_notification_log_due",
            "scheduled_for",
            postgresql_where=sa_text("status = 'pending'"),
        ),
        Index("ix_notification_log_created_at", sa_text("created_at DESC")),
    )

    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "user_id",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_notification_log_user_id"),
            nullable=True,
        ),
    )
    kind: str = Field(sa_column=Column("kind", String(30), nullable=False))
    dedupe_key: str = Field(sa_column=Column("dedupe_key", String(160), nullable=False))
    exhibition_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "exhibition_id",
            Uuid,
            ForeignKey("exhibition.id", ondelete="SET NULL", name="fk_notification_log_exhibition_id"),
            nullable=True,
        ),
    )
    status: str = Field(
        default=NotificationStatus.PENDING,
        sa_column=Column("status", String(10), nullable=False, server_default=sa_text("'pending'")),
    )
    skip_reason: str | None = Field(default=None, sa_column=Column("skip_reason", String(40), nullable=True))
    scheduled_for: _dt.datetime = Field(
        sa_column=Column("scheduled_for", DateTime(timezone=True), nullable=False)
    )
    sent_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("sent_at", DateTime(timezone=True), nullable=True)
    )
    attempt_count: int = Field(
        default=0,
        sa_column=Column("attempt_count", Integer, nullable=False, server_default=sa_text("0")),
    )
    last_error: str | None = Field(default=None, sa_column=Column("last_error", String(300), nullable=True))
    #: 발송 시점 스냅샷. 전시 제목이 나중에 바뀌어도 무엇을 보냈는지 남는다.
    payload: Any | None = Field(default=None, sa_column=Column("payload", JSONB, nullable=True))


class AuditLog(UUIDPKMixin, SQLModel, table=True):
    """관리자 조작 이력 (DB 문서 §4.11).

    비밀번호 해시·전화번호 전체를 담지 않는다. 탈퇴 기록은 탈퇴자를 식별할 값을
    어디에도 남기지 않는다(DB 문서 §10).
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_created_at", sa_text("created_at DESC")),
        Index("ix_audit_log_target", "target_type", "target_id"),
    )

    actor_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "actor_id",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_audit_log_actor_id"),
            nullable=True,
        ),
    )
    #: 시점 스냅샷. 나중에 역할이 바뀌어도 그때의 권한이 남는다.
    actor_role: str | None = Field(default=None, sa_column=Column("actor_role", String(10), nullable=True))
    action: str = Field(sa_column=Column("action", String(60), nullable=False))
    target_type: str | None = Field(default=None, sa_column=Column("target_type", String(40), nullable=True))
    target_id: str | None = Field(default=None, sa_column=Column("target_id", String(64), nullable=True))
    summary: str | None = Field(default=None, sa_column=Column("summary", String(300), nullable=True))
    changes: Any | None = Field(default=None, sa_column=Column("changes", JSONB, nullable=True))
    #: 사용자 문의를 로그와 잇는 유일한 수단 (AP-7).
    request_id: str | None = Field(default=None, sa_column=Column("request_id", String(26), nullable=True))
    created_at: _dt.datetime = Field(sa_column=Column("created_at", DateTime(timezone=True), nullable=False))

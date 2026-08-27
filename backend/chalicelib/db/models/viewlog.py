"""관람 기록 (DB 문서 §4.6–§4.7).

두 테이블 모두 **중복 제거를 제약으로 표현한다.** 집계 시점에 DISTINCT로 걸러 내는
대신 행이 하나만 생기게 만든다 — 지표의 정의가 스키마에 있고 질의마다 재현되지 않는다.

두지 않는 컬럼: 오늘/아카이브 구분, `session_id`, `ip`, `user_agent` (DP-5 최소 수집).
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import text as sa_text
from sqlmodel import Field, SQLModel

from chalicelib.db.models.base import TimestampMixin, UUIDPKMixin


class ViewLog(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """갤러리 입장 기록. **관람일 기준 하루 1행**이 전부다.

    진입 시 UPSERT하며, 충돌 시 `exhibition_id`는 갱신하지 않는다 — 그날 처음 연 전시가
    대표값이다. 아카이브 진입도 같은 입장으로 센다.
    """

    __tablename__ = "view_log"
    __table_args__ = (
        UniqueConstraint("user_id", "viewed_on", name="uq_view_log_user_id_viewed_on"),
        CheckConstraint("entry_count >= 1", name="entry_count_positive"),
        Index("ix_view_log_viewed_on", sa_text("viewed_on DESC")),
        Index("ix_view_log_exhibition_id", "exhibition_id"),
    )

    #: 탈퇴 시 NULL이 된다. 집계 형태는 남기고 식별만 끊는다.
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "user_id",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_view_log_user_id"),
            nullable=True,
        ),
    )
    #: 관람일(KST). 애플리케이션이 계산해 주입한다 — SQL 안에서 CURRENT_DATE를 쓰지 않는다.
    viewed_on: _dt.date = Field(sa_column=Column("viewed_on", Date, nullable=False))
    #: 그날 실제로 걸린 전시.
    exhibition_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "exhibition_id",
            Uuid,
            ForeignKey("exhibition.id", ondelete="SET NULL", name="fk_view_log_exhibition_id"),
            nullable=True,
        ),
    )
    first_entered_at: _dt.datetime = Field(
        sa_column=Column("first_entered_at", DateTime(timezone=True), nullable=False)
    )
    last_entered_at: _dt.datetime = Field(
        sa_column=Column("last_entered_at", DateTime(timezone=True), nullable=False)
    )
    #: 진단용. 지표에는 쓰지 않는다.
    entry_count: int = Field(
        default=1,
        sa_column=Column("entry_count", Integer, nullable=False, server_default=sa_text("1")),
    )
    #: 익명화된 로그는 전 지표의 분모·분자에서 제외된다 (DB 문서 §10).
    is_anonymized: bool = Field(
        default=False,
        sa_column=Column("is_anonymized", Boolean, nullable=False, server_default=sa_text("false")),
    )


class ArtworkViewLog(UUIDPKMixin, TimestampMixin, SQLModel, table=True):
    """그림 열람 기록. **(회원, 그림) 조합당 1행.**

    갤러리 그리드의 "열어봄" 표식은 전시 기준으로 조회한다 — 그래서 `exhibition_id`를
    비정규화해 둔다.
    """

    __tablename__ = "artwork_view_log"
    __table_args__ = (
        UniqueConstraint("user_id", "artwork_id", name="uq_artwork_view_log_user_id_artwork_id"),
        CheckConstraint("view_count >= 1", name="view_count_positive"),
        Index("ix_artwork_view_log_user_id_exhibition_id", "user_id", "exhibition_id"),
        Index("ix_artwork_view_log_first_viewed_on", sa_text("first_viewed_on DESC")),
    )

    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "user_id",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_artwork_view_log_user_id"),
            nullable=True,
        ),
    )
    #: 그림이 교체되면 그 열람 기록은 의미를 잃는다.
    artwork_id: uuid.UUID = Field(
        sa_column=Column(
            "artwork_id",
            Uuid,
            ForeignKey("artwork.id", ondelete="CASCADE", name="fk_artwork_view_log_artwork_id"),
            nullable=False,
        )
    )
    exhibition_id: uuid.UUID = Field(
        sa_column=Column(
            "exhibition_id",
            Uuid,
            ForeignKey("exhibition.id", ondelete="CASCADE", name="fk_artwork_view_log_exhibition_id"),
            nullable=False,
        )
    )
    first_viewed_on: _dt.date = Field(sa_column=Column("first_viewed_on", Date, nullable=False))
    first_viewed_at: _dt.datetime = Field(
        sa_column=Column("first_viewed_at", DateTime(timezone=True), nullable=False)
    )
    last_viewed_at: _dt.datetime = Field(
        sa_column=Column("last_viewed_at", DateTime(timezone=True), nullable=False)
    )
    view_count: int = Field(
        default=1,
        sa_column=Column("view_count", Integer, nullable=False, server_default=sa_text("1")),
    )
    is_anonymized: bool = Field(
        default=False,
        sa_column=Column("is_anonymized", Boolean, nullable=False, server_default=sa_text("false")),
    )

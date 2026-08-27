"""전시와 그림 (DB 문서 §4.4–§4.5).

**드래프트와 발행본이 같은 행이다.** 별도 draft 테이블을 두지 않는다 — 이어쓰기·발행이
같은 행의 상태 전이가 되고, "어느 쪽이 진짜인가"를 묻는 코드가 사라진다.
"""

# `from __future__ import annotations`를 쓰지 않는다 — SQLModel의 `Relationship`이
# 어노테이션 문자열을 그대로 relationship() 인자로 넘겨 매퍼 초기화가 깨진다.
import datetime as _dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
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
from sqlmodel import Field, Relationship, SQLModel

from chalicelib.config.constants import (
    ARTWORK_COUNT,
    ARTWORK_POSITION_MAX,
    ARTWORK_POSITION_MIN,
    LIMIT_ARTWORK_ARTIST,
    LIMIT_ARTWORK_COLLECTION,
    LIMIT_ARTWORK_DESCRIPTION,
    LIMIT_ARTWORK_SOURCE_URL,
    LIMIT_ARTWORK_TITLE,
    LIMIT_ARTWORK_YEAR_TEXT,
    LIMIT_EXHIBITION_THEME,
    LIMIT_EXHIBITION_TITLE,
    LIMIT_HIDDEN_REASON,
)
from chalicelib.db.models.base import TimestampMixin, UUIDPKMixin, VersionMixin
from chalicelib.db.models.enums import ImageStatus, values

#: 완성 판정. 본문 4종이 채워지고 이미지가 `ready`일 때 참이다.
#: `STORED GENERATED`로 두어 판정이 코드에 흩어지지 않게 한다(DB 문서 §4.5).
_IS_COMPLETE_EXPRESSION = (
    "title IS NOT NULL AND btrim(title) <> '' "
    "AND artist IS NOT NULL AND btrim(artist) <> '' "
    "AND year_text IS NOT NULL AND btrim(year_text) <> '' "
    "AND description IS NOT NULL AND btrim(description) <> '' "
    "AND image_status = 'ready'"
)


class Exhibition(UUIDPKMixin, TimestampMixin, VersionMixin, SQLModel, table=True):
    __tablename__ = "exhibition"
    __table_args__ = (
        UniqueConstraint("exhibition_date", name="uq_exhibition_date"),
        CheckConstraint(f"artwork_count BETWEEN 0 AND {ARTWORK_COUNT}", name="artwork_count_range"),
        CheckConstraint(
            f"complete_artwork_count BETWEEN 0 AND {ARTWORK_COUNT}",
            name="complete_artwork_count_range",
        ),
        CheckConstraint("complete_artwork_count <= artwork_count", name="complete_not_over_total"),
        CheckConstraint(
            "(is_published AND published_at IS NOT NULL) OR (NOT is_published AND published_at IS NULL)",
            name="published_consistency",
        ),
        CheckConstraint(
            "(is_hidden AND hidden_at IS NOT NULL) OR (NOT is_hidden AND hidden_at IS NULL)",
            name="hidden_consistency",
        ),
        # 관람자 질의 전용 부분 인덱스. **모든 관람 트래픽이 이 하나를 탄다.**
        Index(
            "ix_exhibition_visible",
            sa_text("exhibition_date DESC"),
            postgresql_where=sa_text("is_published AND NOT is_hidden"),
        ),
    )
    #: 발행일 — 전시에 영구히 귀속된다. 하루에 하나뿐이다.
    exhibition_date: _dt.date = Field(sa_column=Column("exhibition_date", Date, nullable=False))
    title: str | None = Field(
        default=None, sa_column=Column("title", String(LIMIT_EXHIBITION_TITLE), nullable=True)
    )
    theme: str | None = Field(
        default=None, sa_column=Column("theme", String(LIMIT_EXHIBITION_THEME), nullable=True)
    )

    #: 단방향이다. 어떤 수정으로도 false로 되돌리지 않는다(PRD 부록 B).
    is_published: bool = Field(
        default=False,
        sa_column=Column("is_published", Boolean, nullable=False, server_default=sa_text("false")),
    )
    published_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("published_at", DateTime(timezone=True), nullable=True)
    )
    #: 관람자에게서 감추는 유일한 수단.
    is_hidden: bool = Field(
        default=False,
        sa_column=Column("is_hidden", Boolean, nullable=False, server_default=sa_text("false")),
    )
    hidden_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("hidden_at", DateTime(timezone=True), nullable=True)
    )
    hidden_reason: str | None = Field(
        default=None, sa_column=Column("hidden_reason", String(LIMIT_HIDDEN_REASON), nullable=True)
    )
    draft_updated_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("draft_updated_at", DateTime(timezone=True), nullable=True)
    )

    #: 파생 카운터. 그림 변경과 **같은 트랜잭션**에서 재계산한다.
    artwork_count: int = Field(
        default=0,
        sa_column=Column("artwork_count", Integer, nullable=False, server_default=sa_text("0")),
    )
    complete_artwork_count: int = Field(
        default=0,
        sa_column=Column("complete_artwork_count", Integer, nullable=False, server_default=sa_text("0")),
    )

    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            "created_by",
            Uuid,
            ForeignKey("app_user.id", ondelete="SET NULL", name="fk_exhibition_created_by"),
            nullable=True,
        ),
    )

    #: 부모 없이는 존재할 수 없는 컬렉션이므로 delete-orphan을 함께 둔다.
    #: `lazy="raise"`는 의도치 않은 지연 로딩(=N+1의 출처)을 예외로 만든다(백엔드 문서 §4.2).
    artworks: list["Artwork"] = Relationship(
        back_populates="exhibition",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "raise",
            "order_by": "Artwork.position",
        },
    )


class Artwork(UUIDPKMixin, TimestampMixin, VersionMixin, SQLModel, table=True):
    __tablename__ = "artwork"
    __table_args__ = (
        # 순서 변경은 트랜잭션 안에서 일괄 재할당한다. 임시 오프셋 트릭을 쓰지 않는다.
        UniqueConstraint(
            "exhibition_id",
            "position",
            name="uq_artwork_exhibition_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            f"position BETWEEN {ARTWORK_POSITION_MIN} AND {ARTWORK_POSITION_MAX}",
            name="position_range",
        ),
        CheckConstraint(
            f"image_status IN ({', '.join(repr(v) for v in values(ImageStatus))})",
            name="image_status",
        ),
        CheckConstraint("source_url IS NULL OR source_url LIKE 'https://%'", name="source_url_https"),
        # `ready`면 이미지 키가 존재해야 한다 — 상태와 실체가 어긋나지 않게 한다.
        CheckConstraint(
            "image_status <> 'ready' OR "
            "(image_origin_key IS NOT NULL AND image_display_key IS NOT NULL "
            "AND image_thumb_key IS NOT NULL)",
            name="ready_requires_keys",
        ),
        Index("ix_artwork_exhibition_id_position", "exhibition_id", "position"),
    )

    exhibition_id: uuid.UUID = Field(
        sa_column=Column(
            "exhibition_id",
            Uuid,
            ForeignKey("exhibition.id", ondelete="CASCADE", name="fk_artwork_exhibition_id"),
            nullable=False,
        )
    )
    position: int = Field(sa_column=Column("position", Integer, nullable=False))

    title: str | None = Field(
        default=None, sa_column=Column("title", String(LIMIT_ARTWORK_TITLE), nullable=True)
    )
    artist: str | None = Field(
        default=None, sa_column=Column("artist", String(LIMIT_ARTWORK_ARTIST), nullable=True)
    )
    year_text: str | None = Field(
        default=None, sa_column=Column("year_text", String(LIMIT_ARTWORK_YEAR_TEXT), nullable=True)
    )
    description: str | None = Field(
        default=None,
        sa_column=Column("description", String(LIMIT_ARTWORK_DESCRIPTION), nullable=True),
    )
    collection: str | None = Field(
        default=None, sa_column=Column("collection", String(LIMIT_ARTWORK_COLLECTION), nullable=True)
    )
    source_url: str | None = Field(
        default=None, sa_column=Column("source_url", String(LIMIT_ARTWORK_SOURCE_URL), nullable=True)
    )

    image_status: str = Field(
        default=ImageStatus.EMPTY,
        sa_column=Column("image_status", String(10), nullable=False, server_default=sa_text("'empty'")),
    )
    image_origin_key: str | None = Field(
        default=None, sa_column=Column("image_origin_key", String(255), nullable=True)
    )
    image_display_key: str | None = Field(
        default=None, sa_column=Column("image_display_key", String(255), nullable=True)
    )
    image_thumb_key: str | None = Field(
        default=None, sa_column=Column("image_thumb_key", String(255), nullable=True)
    )
    #: 16px 폭 WebP data URL. 블러 플레이스홀더.
    image_lqip: str | None = Field(default=None, sa_column=Column("image_lqip", String(4000), nullable=True))
    image_width: int | None = Field(default=None, sa_column=Column("image_width", Integer, nullable=True))
    image_height: int | None = Field(default=None, sa_column=Column("image_height", Integer, nullable=True))
    image_bytes: int | None = Field(default=None, sa_column=Column("image_bytes", Integer, nullable=True))
    image_mime: str | None = Field(default=None, sa_column=Column("image_mime", String(30), nullable=True))
    image_error_code: str | None = Field(
        default=None, sa_column=Column("image_error_code", String(40), nullable=True)
    )
    image_uploaded_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("image_uploaded_at", DateTime(timezone=True), nullable=True)
    )
    image_ready_at: _dt.datetime | None = Field(
        default=None, sa_column=Column("image_ready_at", DateTime(timezone=True), nullable=True)
    )
    #: 업로드 착지 키. 확정 경로와 분리해 실패한 업로드가 서비스 경로에 남지 않게 한다.
    image_pending_key: str | None = Field(
        default=None, sa_column=Column("image_pending_key", String(255), nullable=True)
    )

    is_complete: bool = Field(
        default=False,
        sa_column=Column(
            "is_complete",
            Boolean,
            Computed(_IS_COMPLETE_EXPRESSION, persisted=True),
            nullable=False,
        ),
    )

    exhibition: Exhibition | None = Relationship(
        back_populates="artworks",
        sa_relationship_kwargs={"passive_deletes": True, "lazy": "raise"},
    )

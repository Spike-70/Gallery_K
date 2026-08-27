"""관리자 전시 편집 스키마 (API 문서 §9.1–§9.12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from chalicelib.config.constants import (
    ARTWORK_COUNT,
    LIMIT_ARTWORK_ARTIST,
    LIMIT_ARTWORK_COLLECTION,
    LIMIT_ARTWORK_DESCRIPTION,
    LIMIT_ARTWORK_SOURCE_URL,
    LIMIT_ARTWORK_TITLE,
    LIMIT_ARTWORK_YEAR_TEXT,
    LIMIT_EXHIBITION_THEME,
    LIMIT_EXHIBITION_TITLE,
    LIMIT_HIDDEN_REASON,
    LIMIT_UPLOAD_FILENAME,
    UPLOAD_MAX_BYTES,
)
from chalicelib.schemas.common import STRICT, ImageSetOut

EditMode = Literal["create", "edit", "carry_draft", "locked"]


# ── 요청 ───────────────────────────────────────────────────────────────────


class CalendarQuery(BaseModel):
    """미지원 파라미터는 무시하지 않고 거부한다 (API 문서 §2.6)."""

    model_config = STRICT

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    direction: Literal["future", "past"] = "future"


class ExhibitionSaveIn(BaseModel):
    """`title`·`theme`을 **항상 함께 보낸다**(PUT 의미론).

    자동저장 주기마다 전체 상태를 덮어쓰는 편이 부분 병합보다 예측 가능하다.
    """

    model_config = STRICT

    title: str | None = Field(default=None, max_length=LIMIT_EXHIBITION_TITLE)
    theme: str | None = Field(default=None, max_length=LIMIT_EXHIBITION_THEME)
    version: int | None = None


class ArtworkSaveIn(BaseModel):
    model_config = STRICT

    title: str | None = Field(default=None, max_length=LIMIT_ARTWORK_TITLE)
    artist: str | None = Field(default=None, max_length=LIMIT_ARTWORK_ARTIST)
    year_text: str | None = Field(default=None, max_length=LIMIT_ARTWORK_YEAR_TEXT)
    description: str | None = Field(default=None, max_length=LIMIT_ARTWORK_DESCRIPTION)
    collection: str | None = Field(default=None, max_length=LIMIT_ARTWORK_COLLECTION)
    source_url: str | None = Field(default=None, max_length=LIMIT_ARTWORK_SOURCE_URL)
    version: int | None = None

    @model_validator(mode="after")
    def _check_source_url(self) -> ArtworkSaveIn:
        if self.source_url and not self.source_url.startswith("https://"):
            raise ValueError("출처 주소는 https:// 로 시작해야 합니다.")
        return self


class ReorderItem(BaseModel):
    model_config = STRICT

    artwork_id: str
    position: int = Field(ge=1, le=ARTWORK_COUNT)


class ReorderIn(BaseModel):
    """전체 슬롯의 **최종 상태 선언**이므로 재시도가 안전하다."""

    model_config = STRICT

    order: list[ReorderItem] = Field(min_length=1, max_length=ARTWORK_COUNT)


class HideIn(BaseModel):
    model_config = STRICT

    reason: str | None = Field(default=None, max_length=LIMIT_HIDDEN_REASON)


class CarryDraftIn(BaseModel):
    model_config = STRICT

    confirm: Literal[True]


# ── 응답 ───────────────────────────────────────────────────────────────────


class DraftProgressOut(BaseModel):
    artwork_count: int
    complete_artwork_count: int
    has_title: bool
    has_theme: bool


class AdminExhibitionDayOut(BaseModel):
    """§3.9 — `edit_mode`를 서버가 결정한다."""

    date: str
    status: Literal["published", "carried_over", "empty"]
    title: str | None
    carried_from_date: str | None
    carried_from_title: str | None
    has_draft: bool
    draft_progress: DraftProgressOut
    is_hidden: bool
    is_editable: bool
    edit_mode: EditMode
    is_today: bool
    updated_at: str | None


class CalendarOut(BaseModel):
    days: list[AdminExhibitionDayOut]


class AdminArtworkSlotOut(BaseModel):
    """§9.3 — 항상 12개이며 비어 있어도 자리 표시자가 온다."""

    position: int
    artwork_id: str | None
    title: str | None
    artist: str | None
    year_text: str | None
    description: str | None
    collection: str | None
    source_url: str | None
    image_status: Literal["empty", "uploading", "ready", "failed"]
    image: ImageSetOut | None
    image_error_code: str | None
    is_complete: bool
    version: int | None


class CarryDraftSourceOut(BaseModel):
    from_date: str
    artwork_count: int


class AdminExhibitionDetailOut(BaseModel):
    """§9.3 — 세 엔드포인트가 이 구조를 참조한다(교차검토 X-23)."""

    exhibition_date: str
    title: str | None
    theme: str | None
    is_published: bool
    published_at: str | None
    is_hidden: bool
    edit_mode: EditMode
    can_publish: bool
    publish_blockers: list[str]
    slots: list[AdminArtworkSlotOut]
    version: int
    draft_updated_at: str | None
    carry_draft_source: CarryDraftSourceOut | None


class ExhibitionSaveOut(BaseModel):
    """§9.4 — `published_now`는 이 요청으로 조건이 처음 충족되었음을 뜻한다."""

    exhibition_date: str
    version: int
    draft_updated_at: str | None
    is_published: bool
    published_at: str | None
    can_publish: bool
    publish_blockers: list[str]
    published_now: bool


class ExhibitionStateOut(BaseModel):
    version: int
    can_publish: bool
    publish_blockers: list[str]
    is_published: bool
    published_now: bool


class ArtworkSaveOut(BaseModel):
    """§9.5 — 전시 상태를 함께 반환해 저장 후 재조회를 없앤다."""

    slot: AdminArtworkSlotOut
    exhibition: ExhibitionStateOut


class ReorderOut(BaseModel):
    slots: list[AdminArtworkSlotOut]


class HideOut(BaseModel):
    """§9.10 — `current_exhibition_date`로 조작 결과를 즉시 확인한다."""

    exhibition_date: str
    is_hidden: bool
    hidden_at: str | None
    current_exhibition_date: str | None


class CarryDraftOut(BaseModel):
    from_date: str
    to_date: str
    moved_artwork_count: int
    exhibition: AdminExhibitionDetailOut


class AdminSummaryOut(BaseModel):
    """§9.1."""

    today_entrant_count: int
    weekly_active_ratio: float
    weekly_active_count: int
    total_member_count: int
    carried_over_days: int
    pending_draft_count: int
    lead_time_days: int


# ── 업로드 (API 문서 §9.8·§9.9) ────────────────────────────────────────────


class UploadFileIn(BaseModel):
    model_config = STRICT

    position: int = Field(ge=1, le=ARTWORK_COUNT)
    filename: str = Field(min_length=1, max_length=LIMIT_UPLOAD_FILENAME)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(ge=1, le=UPLOAD_MAX_BYTES)


class UploadUrlsIn(BaseModel):
    model_config = STRICT

    files: list[UploadFileIn] = Field(min_length=1, max_length=ARTWORK_COUNT)
    #: `true`면 이미 `ready`인 슬롯의 이미지를 교체한다.
    overwrite: bool = False


class UploadCredentialOut(BaseModel):
    position: int
    artwork_id: str
    upload_url: str
    method: Literal["POST"]
    #: 서명 정책 필드 묶음. **순서대로 폼에 담고 파일을 마지막에 붙인다.**
    fields: dict[str, str]
    object_key: str
    expires_at: str


class UploadUrlsOut(BaseModel):
    uploads: list[UploadCredentialOut]


class ImageCompleteIn(BaseModel):
    model_config = STRICT

    object_key: str = Field(min_length=1, max_length=512)


class ImageCompleteOut(BaseModel):
    """§9.9 — 응답이 곧 처리 완료 통지다. 폴링하지 않는다."""

    artwork_id: str
    image_status: Literal["empty", "uploading", "ready", "failed"]
    images: ImageSetOut | None
    image_error_code: str | None

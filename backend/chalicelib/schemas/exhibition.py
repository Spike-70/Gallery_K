"""관람자 API 스키마 (API 문서 §3.2–§3.5·§7)."""

from __future__ import annotations

from pydantic import BaseModel

from chalicelib.schemas.common import ImageSetOut


class ArtworkSummaryOut(BaseModel):
    """§3.2 — 그리드에는 작가명만 보인다. `title`은 대체 텍스트 구성용이다."""

    id: str
    position: int
    artist: str
    title: str
    image: ImageSetOut | None
    is_viewed: bool


class ArtworkDetailOut(ArtworkSummaryOut):
    """§3.3."""

    year_text: str
    description: str
    collection: str | None
    source_url: str | None
    prev_artwork_id: str | None
    next_artwork_id: str | None


class ExhibitionDetailOut(BaseModel):
    """§3.5 — 연장 여부와 문구를 서버가 계산해서 준다."""

    exhibition_date: str
    title: str
    theme: str
    artists: list[str]
    artworks: list[ArtworkSummaryOut]
    viewing_date: str
    is_carried_over: bool
    carried_over_label: str | None
    is_archive_view: bool


class ExhibitionSummaryOut(BaseModel):
    """§3.4."""

    exhibition_date: str
    title: str
    cover_image: ImageSetOut | None
    artwork_count: int
    viewed_artwork_count: int
    is_viewed: bool


class ArchiveOut(BaseModel):
    exhibitions: list[ExhibitionSummaryOut]


class ExhibitionContextOut(BaseModel):
    exhibition_date: str
    title: str
    is_carried_over: bool
    carried_over_label: str | None


class ArtworkDetailResponseOut(BaseModel):
    """§7.5 — 새로고침·딥링크 진입에서도 단독으로 화면을 구성할 수 있어야 한다."""

    artwork: ArtworkDetailOut
    exhibition: ExhibitionContextOut
    position_label: str


class EntryRecordedOut(BaseModel):
    """§7.4 — 관람일은 서버가 결정한다."""

    viewed_on: str
    is_first_entry_today: bool


class ArtworkViewRecordedOut(BaseModel):
    """§7.6."""

    viewed_artwork_count: int

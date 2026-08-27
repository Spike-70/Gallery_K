import { toArtworkSummary, toImageSet } from '@/entities/artwork/api/mappers'
import type { Exhibition, ExhibitionSummary } from '@/entities/exhibition/model/types'
import type { RawExhibitionDetail, RawExhibitionSummary } from '@/shared/api/types'

export function toExhibition(raw: RawExhibitionDetail): Exhibition {
  return {
    date: raw.exhibition_date,
    title: raw.title,
    theme: raw.theme,
    artists: raw.artists,
    artworks: raw.artworks.map(toArtworkSummary),
    viewingDate: raw.viewing_date,
    isCarriedOver: raw.is_carried_over,
    carriedOverLabel: raw.carried_over_label,
    isArchiveView: raw.is_archive_view,
  }
}

export function toExhibitionSummary(raw: RawExhibitionSummary): ExhibitionSummary {
  return {
    date: raw.exhibition_date,
    title: raw.title,
    coverImage: raw.cover_image ? toImageSet(raw.cover_image) : null,
    artworkCount: raw.artwork_count,
    viewedArtworkCount: raw.viewed_artwork_count,
    isViewed: raw.is_viewed,
  }
}

import type { RawArtworkDetail, RawArtworkDetailResponse, RawArtworkSummary, RawImageSet } from '@/shared/api/types'

import type { ArtworkDetail, ArtworkSummary, ArtworkView, ImageSet } from '@/entities/artwork/model/types'

export function toImageSet(raw: RawImageSet): ImageSet {
  return {
    thumbUrl: raw.thumb_url,
    displayUrl: raw.display_url,
    originUrl: raw.origin_url,
    lqip: raw.lqip,
    width: raw.width,
    height: raw.height,
    aspectRatio: raw.aspect_ratio,
  }
}

export function toArtworkSummary(raw: RawArtworkSummary): ArtworkSummary {
  return {
    id: raw.id,
    position: raw.position,
    artist: raw.artist,
    title: raw.title,
    image: toImageSet(raw.image),
    isViewed: raw.is_viewed,
  }
}

export function toArtworkDetail(raw: RawArtworkDetail): ArtworkDetail {
  return {
    ...toArtworkSummary(raw),
    yearText: raw.year_text,
    description: raw.description,
    collection: raw.collection,
    sourceUrl: raw.source_url,
    prevArtworkId: raw.prev_artwork_id,
    nextArtworkId: raw.next_artwork_id,
  }
}

export function toArtworkView(raw: RawArtworkDetailResponse): ArtworkView {
  return {
    artwork: toArtworkDetail(raw.artwork),
    exhibition: {
      date: raw.exhibition.exhibition_date,
      title: raw.exhibition.title,
      isCarriedOver: raw.exhibition.is_carried_over,
      carriedOverLabel: raw.exhibition.carried_over_label,
    },
    positionLabel: raw.position_label,
  }
}

import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawArtworkDetailResponse } from '@/shared/api/types'
import type { Uuid } from '@/shared/types/utility'

import { toArtworkView } from '@/entities/artwork/api/mappers'
import type { ArtworkView } from '@/entities/artwork/model/types'

/** `GET /artworks/{id}` — API 명세서 §7.5 */
export async function fetchArtwork(artworkId: Uuid): Promise<ArtworkView> {
  const raw = await httpClient.get<RawArtworkDetailResponse>(endpoints.artworks.detail(artworkId))
  return toArtworkView(raw)
}

/**
 * `POST /artworks/{id}/view` — 열람 기록
 * **실패해도 조용히 포기한다.** 사용자에게 오류를 보여주지 않는다(FA-7).
 */
export async function logArtworkView(artworkId: Uuid): Promise<number | null> {
  try {
    const raw = await httpClient.post<{ viewed_artwork_count: number }>(
      endpoints.artworks.view(artworkId),
    )
    return raw.viewed_artwork_count
  } catch {
    return null
  }
}

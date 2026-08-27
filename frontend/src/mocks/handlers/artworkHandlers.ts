import { ERROR_CODES } from '@/shared/api/ApiError'
import type { RawArtworkDetailResponse } from '@/shared/api/types'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { formatMonthDay } from '@/shared/lib/date'
import { templates } from '@/shared/config/messages'
import type { Uuid } from '@/shared/types/utility'

import { db, findArtwork, viewedCount } from '@/mocks/db'
import { mockDelay, mockFail } from '@/mocks/lib/mockClient'
import { requireMember, toArtworkDetail } from '@/mocks/lib/serializers'

/**
 * `GET /artworks/{id}` — API 명세서 §7.5
 * 새로고침·딥링크 진입에서도 단독으로 화면을 구성할 수 있도록 전시 문맥을 함께 담는다.
 */
export async function getArtwork(artworkId: Uuid): Promise<RawArtworkDetailResponse> {
  requireMember()
  const found = findArtwork(artworkId)
  if (!found || !found.exhibition.isPublished) {
    mockFail(ERROR_CODES.artworkNotFound, 404)
  }

  const { exhibition, slot } = found
  const isCarriedOver = exhibition.date < db.today
  return mockDelay(
    {
      artwork: toArtworkDetail(exhibition, slot),
      exhibition: {
        exhibition_date: exhibition.date,
        title: exhibition.title ?? '',
        is_carried_over: isCarriedOver,
        carried_over_label: isCarriedOver ? `${formatMonthDay(exhibition.date)}의 전시` : null,
      },
      position_label: templates.positionLabel(slot.position, ARTWORK_COUNT),
    },
    280,
  )
}

/** `POST /artworks/{id}/view` — 1.5초 체류 후에만 호출된다(프런트 §9.3) */
export async function logArtworkView(artworkId: Uuid): Promise<{ viewed_artwork_count: number }> {
  requireMember()
  const found = findArtwork(artworkId)
  if (!found) {
    mockFail(ERROR_CODES.artworkNotFound, 404)
  }
  db.viewedArtworks.add(`${found.exhibition.date}:${artworkId}`)
  return mockDelay({ viewed_artwork_count: viewedCount(found.exhibition.date) }, 100)
}

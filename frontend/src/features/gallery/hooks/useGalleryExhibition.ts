import { useEffect } from 'react'

import { useArtworkPrefetch } from '@/entities/artwork/api/queries'
import {
  useCurrentExhibitionQuery,
  useExhibitionByDateQuery,
} from '@/entities/exhibition/api/queries'
import { useGalleryContext } from '@/entities/exhibition/model/useGalleryContext'
import { trackExhibitionEntry } from '@/app/analytics/viewTracker'

/**
 * C 화면 데이터 — 프런트엔드 아키텍처 문서 §8.1
 *
 * 데이터 소스는 문맥이 결정한다: `/gallery`는 `current`, `/archive/:date`는 그 날짜.
 * 렌더 완료 후 입장 기록을 보내고(§9.3), 첫 그림을 프리페치한다(§9.4).
 */
export function useGalleryExhibition() {
  const context = useGalleryContext()
  const isArchive = context.mode === 'archive'

  const currentQuery = useCurrentExhibitionQuery(!isArchive)
  const archiveQuery = useExhibitionByDateQuery(isArchive ? (context.date ?? undefined) : undefined)
  const query = isArchive ? archiveQuery : currentQuery

  const prefetchArtwork = useArtworkPrefetch()
  const exhibition = query.data

  useEffect(() => {
    if (!exhibition) return
    // 화면에 **실제로 렌더된 전시의 발행일**을 보낸다(API 문서 §7.4).
    trackExhibitionEntry(exhibition.date)
    prefetchArtwork(exhibition.artworks[0]?.id)
  }, [exhibition, prefetchArtwork])

  return { context, query, exhibition, prefetchArtwork }
}

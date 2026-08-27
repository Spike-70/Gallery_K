import { useEffect } from 'react'

import { trackArtworkView } from '@/app/analytics/viewTracker'
import { useMarkArtworkViewed } from '@/entities/exhibition/api/queries'
import { ARTWORK_VIEW_DWELL_MS } from '@/shared/config/constants'
import type { Uuid } from '@/shared/types/utility'

/**
 * 열람 기록 — 프런트엔드 아키텍처 문서 §9.3
 *
 * **1.5초 체류 후에만** 전송한다. 스와이프로 스쳐 지나간 그림을 세면
 * "일 감상 그림 수" 지표가 무의미해진다(F-7).
 *
 * 같은 순간에 **열람 표식을 낙관적으로 반영**한다(§6.4) — 갤러리로 돌아왔을 때
 * 방금 본 그림에 표식이 없으면 사용자는 본 것을 또 연다.
 */
export function useArtworkViewLog(artworkId: Uuid | undefined): void {
  const markViewed = useMarkArtworkViewed()

  useEffect(() => {
    if (!artworkId) return
    const timer = window.setTimeout(() => {
      trackArtworkView(artworkId)
      markViewed(artworkId)
    }, ARTWORK_VIEW_DWELL_MS)
    return () => window.clearTimeout(timer)
  }, [artworkId, markViewed])
}

import { useEffect } from 'react'

import { trackArtworkView } from '@/app/analytics/viewTracker'
import { ARTWORK_VIEW_DWELL_MS } from '@/shared/config/constants'
import type { Uuid } from '@/shared/types/utility'

/**
 * 열람 기록 — 프런트엔드 아키텍처 문서 §9.3
 *
 * **1.5초 체류 후에만** 전송한다. 스와이프로 스쳐 지나간 그림을 세면
 * "일 감상 그림 수" 지표가 무의미해진다(F-7).
 */
export function useArtworkViewLog(artworkId: Uuid | undefined): void {
  useEffect(() => {
    if (!artworkId) return
    const timer = window.setTimeout(() => trackArtworkView(artworkId), ARTWORK_VIEW_DWELL_MS)
    return () => window.clearTimeout(timer)
  }, [artworkId])
}

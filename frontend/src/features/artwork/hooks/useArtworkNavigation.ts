import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { useArtworkPrefetch } from '@/entities/artwork/api/queries'
import type { ArtworkView } from '@/entities/artwork/model/types'
import { useGalleryContext } from '@/entities/exhibition/model/useGalleryContext'
import type { Uuid } from '@/shared/types/utility'

/**
 * 그림 사이 이동 — UX 설계서 §3.8
 *
 * 스와이프·좌우 화살표 키·하단 링크가 **같은 함수**를 호출한다. 제스처에는 항상
 * 대체 수단이 있어야 하므로(UX-7) 이동 로직을 한곳에 모은다.
 *
 * 양 끝에서는 순환하지 않는다 — 끝이 있어야 한다(UX-2).
 */
export function useArtworkNavigation(view: ArtworkView | undefined) {
  const navigate = useNavigate()
  const context = useGalleryContext()
  const prefetch = useArtworkPrefetch()

  const prevId = view?.artwork.prevArtworkId ?? null
  const nextId = view?.artwork.nextArtworkId ?? null

  const goTo = useCallback(
    (artworkId: Uuid | null) => {
      if (!artworkId) return
      navigate(context.artworkPath(artworkId))
    },
    [navigate, context],
  )

  // 인접 그림을 유휴 시간에 미리 받는다 — 전환이 즉시여야 12회 탭 완주가 성립한다(F-1).
  useEffect(() => {
    prefetch(prevId)
    prefetch(nextId)
  }, [prevId, nextId, prefetch])

  // 스와이프의 대체 수단: 좌우 화살표 키
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') goTo(prevId)
      if (event.key === 'ArrowRight') goTo(nextId)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [goTo, prevId, nextId])

  return { context, prevId, nextId, goPrev: () => goTo(prevId), goNext: () => goTo(nextId) }
}

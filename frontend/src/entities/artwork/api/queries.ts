import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import * as artworkApi from '@/entities/artwork/api/artworkApi'
import { artworkKeys } from '@/entities/artwork/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { shouldPrefetch } from '@/shared/lib/platform'
import type { ArtworkView } from '@/entities/artwork/model/types'
import type { Uuid } from '@/shared/types/utility'

/** 그림 상세 — 과거 데이터는 불변이므로 무한 캐시한다(§6.3) */
export function useArtworkQuery(artworkId: Uuid | undefined) {
  return useQuery({
    queryKey: artworkKeys.detail(artworkId ?? ''),
    queryFn: () => artworkApi.fetchArtwork(artworkId as Uuid),
    enabled: Boolean(artworkId),
    ...CACHE_POLICY.artwork,
  })
}

/**
 * 캐시에 이미 있는 그림만 꺼낸다. **없으면 요청하지 않는다** —
 * 스와이프 미리보기는 있으면 좋은 것이지 새 왕복을 만들 이유가 아니다.
 */
export function useCachedArtwork(artworkId: Uuid | null | undefined) {
  const queryClient = useQueryClient()
  if (!artworkId) return undefined
  return queryClient.getQueryData<ArtworkView>(artworkKeys.detail(artworkId))
}

/**
 * 프리페치 — 프런트엔드 아키텍처 문서 §9.4
 * 데이터 절약 모드·2G에서는 전부 비활성화한다.
 */
export function useArtworkPrefetch() {
  const queryClient = useQueryClient()

  return useCallback(
    (artworkId: Uuid | null | undefined) => {
      if (!artworkId || !shouldPrefetch()) return
      void queryClient.prefetchQuery({
        queryKey: artworkKeys.detail(artworkId),
        queryFn: () => artworkApi.fetchArtwork(artworkId),
        ...CACHE_POLICY.artwork,
      })
    },
    [queryClient],
  )
}

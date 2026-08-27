import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import * as artworkApi from '@/entities/artwork/api/artworkApi'
import { artworkKeys } from '@/entities/artwork/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { shouldPrefetch } from '@/shared/lib/platform'
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

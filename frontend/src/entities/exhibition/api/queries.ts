import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import * as exhibitionApi from '@/entities/exhibition/api/exhibitionApi'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { ARCHIVE_LIMIT } from '@/shared/config/constants'
import type { Exhibition } from '@/entities/exhibition/model/types'
import type { IsoDate, Uuid } from '@/shared/types/utility'

/** C 화면. 포커스 복귀 시 새 전시를 확인한다(§6.3) */
export function useCurrentExhibitionQuery(enabled = true) {
  return useQuery({
    queryKey: exhibitionKeys.current(),
    queryFn: exhibitionApi.fetchCurrentExhibition,
    enabled,
    ...CACHE_POLICY.currentExhibition,
    refetchOnWindowFocus: true,
  })
}

/** 아카이브 상세. 과거 전시는 불변이므로 재검증하지 않는다 */
export function useExhibitionByDateQuery(date: IsoDate | undefined) {
  return useQuery({
    queryKey: exhibitionKeys.byDate(date ?? ''),
    queryFn: () => exhibitionApi.fetchExhibitionByDate(date as IsoDate),
    enabled: Boolean(date),
    ...CACHE_POLICY.pastExhibition,
  })
}

/** C-3 목록. 무한 스크롤은 30개에서 끝난다(UX-2 — 끝이 있다) */
export function useArchiveQuery() {
  return useInfiniteQuery({
    queryKey: exhibitionKeys.archive({ limit: ARCHIVE_LIMIT }),
    queryFn: ({ pageParam }) => exhibitionApi.fetchArchive({ cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    ...CACHE_POLICY.archive,
  })
}

/**
 * 열람 표식 낙관 반영 — 프런트엔드 아키텍처 문서 §6.4, UX §10
 *
 * 그림을 보고 갤러리로 돌아왔는데 표식이 없으면 사용자는 **본 것을 또 연다.**
 * 전시 쿼리는 5분간 신선하다고 여겨져 다시 받지 않으므로, 캐시를 직접 고쳐야 한다.
 *
 * **기록 API가 실패해도 롤백하지 않는다.** 사용자가 본 것은 사실이고,
 * 서버가 그것을 못 받은 일로 화면을 되돌리면 더 이상하다.
 */
export function useMarkArtworkViewed() {
  const queryClient = useQueryClient()

  return useCallback(
    (artworkId: Uuid) => {
      const mark = (exhibition: Exhibition | undefined): Exhibition | undefined => {
        if (!exhibition) return exhibition
        if (!exhibition.artworks.some((artwork) => artwork.id === artworkId && !artwork.isViewed)) {
          return exhibition
        }
        return {
          ...exhibition,
          artworks: exhibition.artworks.map((artwork) =>
            artwork.id === artworkId ? { ...artwork, isViewed: true } : artwork,
          ),
        }
      }

      // 오늘의 전시와 아카이브 상세 어느 쪽에서 열었는지 화면은 모른다. 둘 다 고친다.
      queryClient.setQueryData<Exhibition>(exhibitionKeys.current(), mark)
      queryClient.setQueriesData<Exhibition>({ queryKey: ['exhibition', 'date'] }, mark)
    },
    [queryClient],
  )
}

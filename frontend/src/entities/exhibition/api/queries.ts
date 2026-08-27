import { useInfiniteQuery, useQuery } from '@tanstack/react-query'

import * as exhibitionApi from '@/entities/exhibition/api/exhibitionApi'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { ARCHIVE_LIMIT } from '@/shared/config/constants'
import type { IsoDate } from '@/shared/types/utility'

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

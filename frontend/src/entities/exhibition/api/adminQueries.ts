import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import * as adminApi from '@/entities/exhibition/api/adminExhibitionApi'
import { adminExhibitionKeys } from '@/entities/exhibition/api/adminKeys'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { CALENDAR_PAGE_SIZE } from '@/shared/config/constants'
import { shouldPrefetch } from '@/shared/lib/platform'
import type { IsoDate } from '@/shared/types/utility'

/**
 * 관리자 전시 쿼리 — 프런트엔드 아키텍처 문서 §6.3
 * 운영 데이터는 `staleTime: 0`이다. 항상 최신을 본다.
 */

export function useAdminSummaryQuery() {
  return useQuery({
    queryKey: adminExhibitionKeys.summary(),
    queryFn: adminApi.fetchAdminSummary,
    ...CACHE_POLICY.admin,
    refetchOnWindowFocus: true,
  })
}

/**
 * 달력 — API 문서 §9.2
 *
 * **두 방향은 커서 공간이 서로 다르다.** 한 무한 쿼리에 섞으면 `next_cursor`가
 * 어느 방향의 것인지 알 수 없어진다. 그래서 방향마다 쿼리를 따로 둔다.
 *
 * - `future`: 오늘을 맨 위로 하는 7일치. 아래로 스크롤하면 30일씩 이어 받는다.
 * - `past`: 위로 스크롤할 때만 켜진다. **과거 전시 수정 경로가 이 쿼리다**(PRD GAP-7).
 */
export function useCalendarQuery() {
  return useInfiniteQuery({
    queryKey: adminExhibitionKeys.calendar({ direction: 'future' }),
    queryFn: ({ pageParam }) => adminApi.fetchCalendar({ direction: 'future', cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    ...CACHE_POLICY.admin,
  })
}

export function usePastCalendarQuery(enabled: boolean) {
  return useInfiniteQuery({
    queryKey: adminExhibitionKeys.calendar({ direction: 'past' }),
    queryFn: ({ pageParam }) =>
      adminApi.fetchCalendar({ direction: 'past', cursor: pageParam, limit: CALENDAR_PAGE_SIZE }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    enabled,
    ...CACHE_POLICY.admin,
  })
}

/**
 * 편집 상태 조회.
 * 이미지 처리는 업로드 완료 통지 응답으로 끝나므로(API 문서 §9.9) **폴링하지 않는다.**
 * 업로드가 끝나면 업로드 큐가 이 쿼리를 무효화한다.
 */
export function useAdminExhibitionQuery(date: IsoDate | undefined) {
  return useQuery({
    queryKey: adminExhibitionKeys.exhibition(date ?? ''),
    queryFn: () => adminApi.fetchAdminExhibition(date as IsoDate),
    enabled: Boolean(date),
    ...CACHE_POLICY.admin,
  })
}

/** `/admin` 진입 시 오늘 칸을 미리 받아 둔다 — 데이터 절약 모드에서는 하지 않는다(§9.4). */
export function usePrefetchAdminExhibition() {
  const queryClient = useQueryClient()
  return useCallback(
    (date: IsoDate) => {
      if (!shouldPrefetch()) return
      void queryClient.prefetchQuery({
        queryKey: adminExhibitionKeys.exhibition(date),
        queryFn: () => adminApi.fetchAdminExhibition(date),
        ...CACHE_POLICY.admin,
      })
    },
    [queryClient],
  )
}

export function useExhibitionPreviewQuery(date: IsoDate | undefined) {
  return useQuery({
    queryKey: adminExhibitionKeys.preview(date ?? ''),
    queryFn: () => adminApi.fetchExhibitionPreview(date as IsoDate),
    enabled: Boolean(date),
    ...CACHE_POLICY.admin,
  })
}

/**
 * 저장 후 무효화 — 접두 매칭 하나로 달력·편집·관람자 화면이 모두 갱신된다(§7.3).
 * 관람자 캐시까지 지우는 이유는 발행 조건이 충족되면 즉시 걸리기 때문이다.
 */
function useInvalidateAdmin() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: adminExhibitionKeys.all })
    void queryClient.invalidateQueries({ queryKey: exhibitionKeys.all })
  }
}

export function useSaveExhibitionMetaMutation(date: IsoDate) {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: (input: { title: string | null; theme: string | null; version?: number }) =>
      adminApi.saveExhibitionMeta(date, input),
    onSuccess: invalidate,
  })
}

export function useSaveArtworkSlotMutation(date: IsoDate) {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: ({
      position,
      ...input
    }: {
      position: number
      title: string | null
      artist: string | null
      yearText: string | null
      description: string | null
      collection: string | null
      sourceUrl: string | null
      version?: number
    }) => adminApi.saveArtworkSlot(date, position, input),
    onSuccess: invalidate,
  })
}

export function useClearArtworkSlotMutation(date: IsoDate) {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: (position: number) => adminApi.clearArtworkSlot(date, position),
    onSuccess: invalidate,
  })
}

export function useReorderArtworksMutation(date: IsoDate) {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: (order: { artworkId: string; position: number }[]) =>
      adminApi.reorderArtworks(date, order),
    onSuccess: invalidate,
  })
}

export function useCarryDraftMutation() {
  const invalidate = useInvalidateAdmin()
  return useMutation({ mutationFn: adminApi.carryDraft, onSuccess: invalidate })
}

/**
 * 전시 숨김·숨김 해제 — PRD §6.9
 *
 * **되돌리기 어려운 조작이므로 낙관적 반영을 하지 않는다**(프런트 §6.4).
 * 숨기면 아카이브에서 빠지고, 현재 걸려 있던 전시였다면 직전 전시가 대신 연장되므로
 * 관람자 캐시까지 함께 무효화한다.
 */
export function useSetExhibitionHiddenMutation() {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: ({ date, hidden }: { date: IsoDate; hidden: boolean }) =>
      adminApi.setExhibitionHidden(date, hidden),
    onSuccess: invalidate,
  })
}

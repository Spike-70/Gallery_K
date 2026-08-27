import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import * as adminApi from '@/entities/exhibition/api/adminExhibitionApi'
import { adminExhibitionKeys } from '@/entities/exhibition/api/adminKeys'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { IMAGE_POLL_INTERVAL_MS } from '@/shared/config/constants'
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

/** 오늘을 맨 위로 하는 7일치. 아래로 스크롤하면 미래 30일씩 이어 받는다(API 문서 §9.2). */
export function useCalendarQuery() {
  return useInfiniteQuery({
    queryKey: adminExhibitionKeys.calendar({ direction: 'future' }),
    queryFn: ({ pageParam }) => adminApi.fetchCalendar({ direction: 'future', cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    ...CACHE_POLICY.admin,
  })
}

/**
 * 편집 상태 조회.
 * 이미지가 `uploading`·`processing`인 동안에만 2초 간격으로 다시 조회한다(API 문서 §9.9).
 * 폴링 조건을 쿼리 자신이 갖고 있어야 화면이 조건을 재구현하지 않는다.
 */
export function useAdminExhibitionQuery(date: IsoDate | undefined) {
  return useQuery({
    queryKey: adminExhibitionKeys.exhibition(date ?? ''),
    queryFn: () => adminApi.fetchAdminExhibition(date as IsoDate),
    enabled: Boolean(date),
    refetchInterval: (query) => {
      const pending = query.state.data?.slots.some(
        (slot) => slot.imageStatus === 'processing' || slot.imageStatus === 'uploading',
      )
      return pending ? IMAGE_POLL_INTERVAL_MS : false
    },
    ...CACHE_POLICY.admin,
  })
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

export function useSetExhibitionHiddenMutation() {
  const invalidate = useInvalidateAdmin()
  return useMutation({
    mutationFn: ({ date, hidden }: { date: IsoDate; hidden: boolean }) =>
      adminApi.setExhibitionHidden(date, hidden),
    onSuccess: invalidate,
  })
}

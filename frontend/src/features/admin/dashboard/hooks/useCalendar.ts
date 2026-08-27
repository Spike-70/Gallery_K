import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

import {
  useCalendarQuery,
  useCarryDraftMutation,
  usePastCalendarQuery,
  usePrefetchAdminExhibition,
} from '@/entities/exhibition/api/adminQueries'
import type { AdminExhibitionDay } from '@/entities/exhibition/model/admin'
import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { screens } from '@/shared/config/messages'
import { toast } from '@/shared/ui'

/**
 * B 관리자 홈의 달력 — UX 설계서 §3.11
 *
 * 목록은 **오늘을 기준으로 양쪽으로 자란다.** 아래로는 미래 30일씩, 위로는 과거 30일씩.
 * 과거 방향이 없으면 이미 지나간 전시를 고칠 길이 사라진다(PRD GAP-7).
 *
 * 위로 늘어날 때는 **스크롤 위치를 보정한다.** 보정하지 않으면 새 행이 위에 끼어들면서
 * 보고 있던 날짜가 화면 밖으로 밀려난다.
 *
 * 이어쓰기는 확인 다이얼로그를 거친다. 대상 날짜에 이미 작업물이 있으면
 * 다이얼로그 대신 안내를 띄운다(`DRAFT_TARGET_OCCUPIED`).
 */
export function useCalendar() {
  const query = useCalendarQuery()
  const [pastEnabled, setPastEnabled] = useState(false)
  const pastQuery = usePastCalendarQuery(pastEnabled)
  const carryMutation = useCarryDraftMutation()

  const [carryTarget, setCarryTarget] = useState<AdminExhibitionDay | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)

  const futureDays = query.data?.pages.flatMap((page) => page.items) ?? []
  const todayDate = futureDays.find((day) => day.isToday)?.date ?? ''

  /**
   * 관리자 홈에 들어오면 **오늘의 편집 데이터를 미리 받는다**(§9.4).
   * 큐레이터가 홈에서 하는 일은 거의 언제나 "오늘 칸을 연다"이다.
   */
  const prefetchToday = usePrefetchAdminExhibition()
  useEffect(() => {
    if (todayDate) prefetchToday(todayDate)
  }, [todayDate, prefetchToday])

  /**
   * 과거 페이지는 **가까운 과거부터** 온다(0쪽 = 어제까지의 30일).
   * 화면에서는 오래된 날짜가 위에 와야 하므로 페이지 순서를 뒤집어 이어 붙인다.
   */
  const pastDays = [...(pastQuery.data?.pages ?? [])].reverse().flatMap((page) => page.items)
  const days = [...pastDays, ...futureDays]

  // ── 위쪽 성장 시 스크롤 보정 ──────────────────────────────────────────
  const anchorHeight = useRef<number | null>(null)

  const loadPast = useCallback(() => {
    if (!pastEnabled) {
      anchorHeight.current = document.documentElement.scrollHeight
      setPastEnabled(true)
      return
    }
    if (pastQuery.isFetchingNextPage || !pastQuery.hasNextPage) return
    anchorHeight.current = document.documentElement.scrollHeight
    void pastQuery.fetchNextPage()
  }, [pastEnabled, pastQuery])

  useLayoutEffect(() => {
    if (anchorHeight.current === null) return
    const grew = document.documentElement.scrollHeight - anchorHeight.current
    if (grew > 0) {
      anchorHeight.current = null
      window.scrollBy({ top: grew, behavior: 'instant' as ScrollBehavior })
    }
  }, [pastDays.length])

  const loadFuture = useCallback(() => {
    if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage()
  }, [query])

  const confirmCarry = async () => {
    if (!carryTarget) return
    try {
      await carryMutation.mutateAsync(carryTarget.date)
      setCarryTarget(null)
    } catch (error) {
      setCarryTarget(null)
      if (isApiError(error) && error.code === ERROR_CODES.draftTargetOccupied) {
        setBlockedMessage(screens.admin.carryBlocked)
        return
      }
      toast.error(resolveErrorMessage(error))
    }
  }

  return {
    query,
    days,
    /** 오늘 행의 날짜 — 이어쓰기 다이얼로그가 대상 날짜를 표시하는 데 쓴다 */
    todayDate,
    loadPast,
    loadFuture,
    hasMorePast: !pastEnabled || (pastQuery.hasNextPage ?? false),
    loadingPast: pastQuery.isFetching,
    carryTarget,
    setCarryTarget,
    confirmCarry,
    carrying: carryMutation.isPending,
    blockedMessage,
    clearBlocked: () => setBlockedMessage(null),
  }
}

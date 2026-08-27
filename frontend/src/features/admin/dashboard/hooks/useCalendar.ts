import { useEffect, useState } from 'react'

import { useCalendarQuery, useCarryDraftMutation } from '@/entities/exhibition/api/adminQueries'
import type { AdminExhibitionDay } from '@/entities/exhibition/model/admin'
import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { screens } from '@/shared/config/messages'
import { toast } from '@/shared/ui'

/**
 * B 관리자 홈의 달력 — UX 설계서 §3.11
 *
 * 이어쓰기는 확인 다이얼로그를 거친다. 대상 날짜에 이미 작업물이 있으면
 * 다이얼로그 대신 안내를 띄운다(`DRAFT_TARGET_OCCUPIED`).
 */
export function useCalendar() {
  const query = useCalendarQuery()
  const carryMutation = useCarryDraftMutation()

  const [carryTarget, setCarryTarget] = useState<AdminExhibitionDay | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)

  const days = query.data?.pages.flatMap((page) => page.items) ?? []

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

  // 스크롤 없이도 첫 화면에 오늘이 맨 위에 오도록 보장한다(PRD §6.9).
  useEffect(() => {
    if (days.length > 0 && !days[0].isToday) {
      void query.refetch()
    }
    // 최초 1회만 확인한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    query,
    days,
    carryTarget,
    setCarryTarget,
    confirmCarry,
    carrying: carryMutation.isPending,
    blockedMessage,
    clearBlocked: () => setBlockedMessage(null),
  }
}

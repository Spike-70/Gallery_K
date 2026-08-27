import { useEffect, useRef } from 'react'

import { useAdminSummaryQuery } from '@/entities/exhibition/api/adminQueries'
import { DayRow } from '@/features/admin/dashboard/components/DayRow'
import { SummaryStats } from '@/features/admin/dashboard/components/SummaryStats'
import { useCalendar } from '@/features/admin/dashboard/hooks/useCalendar'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { actions, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useIntersection } from '@/shared/hooks/useIntersection'
import { formatShortDate } from '@/shared/lib/date'
import { AlertDialog, BackLink, Dialog, ErrorState, Skeleton, TextLink } from '@/shared/ui'
import { resolveErrorMessage } from '@/shared/api/errorMessages'

/**
 * B. 관리자 홈 — UX 설계서 §3.11
 *
 * **목적은 하나다: "어느 날이 비어 있는가"를 1초 안에 알게 한다.**
 * 요약 줄이 실패해도 목록은 정상 렌더한다.
 */
export function AdminDashboardPage() {
  const summaryQuery = useAdminSummaryQuery()
  const calendar = useCalendar()
  const sentinelRef = useRef<HTMLDivElement>(null)
  const reachedEnd = useIntersection(sentinelRef)

  useEffect(() => {
    if (reachedEnd && calendar.query.hasNextPage && !calendar.query.isFetchingNextPage) {
      void calendar.query.fetchNextPage()
    }
  }, [reachedEnd, calendar.query])

  const target = calendar.carryTarget

  return (
    <>
      <SummaryStats summary={summaryQuery.data} isLoading={summaryQuery.isPending} />

      <nav className="flex gap-4 py-4" aria-label="관리 메뉴">
        <TextLink to={paths.adminStats}>{screens.admin.statsLink}</TextLink>
        <TextLink to={paths.adminMembers}>{screens.admin.membersLink}</TextLink>
        <TextLink to={paths.adminSettings}>{screens.admin.settingsLink}</TextLink>
      </nav>

      {calendar.query.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 7 }, (_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      ) : calendar.query.isError ? (
        <ErrorState
          message={resolveErrorMessage(calendar.query.error)}
          onRetry={() => void calendar.query.refetch()}
        />
      ) : (
        <ul className="list-none p-0">
          {calendar.days.map((day) => (
            <DayRow key={day.date} day={day} onCarryDraft={calendar.setCarryTarget} />
          ))}
        </ul>
      )}

      <div ref={sentinelRef} className="py-4" />

      <BackLink to={paths.landing} label={actions.backHome} />

      {/* 이어쓰기 확인 — 이동이지 복사가 아니다. 원본 날짜는 비워진다. */}
      <Dialog
        open={Boolean(target)}
        title={target ? screens.admin.carryDialogTitle(formatShortDate(target.date)) : ''}
        description={
          target
            ? screens.admin.carryDialogBody(
                target.draftProgress.artworkCount || ARTWORK_COUNT,
                formatShortDate(target.date),
                calendar.days.find((day) => day.isToday)?.date ?? '',
              )
            : undefined
        }
        confirmLabel={actions.move}
        loading={calendar.carrying}
        onConfirm={() => void calendar.confirmCarry()}
        onClose={() => calendar.setCarryTarget(null)}
      />

      <AlertDialog
        open={Boolean(calendar.blockedMessage)}
        title={calendar.blockedMessage ?? ''}
        onClose={calendar.clearBlocked}
      />
    </>
  )
}

import { useEffect } from 'react'

import { useAdminSummaryQuery } from '@/entities/exhibition/api/adminQueries'
import { DayRow } from '@/features/admin/dashboard/components/DayRow'
import { SummaryStats } from '@/features/admin/dashboard/components/SummaryStats'
import { useCalendar } from '@/features/admin/dashboard/hooks/useCalendar'
import { actions, landmarks, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useIntersection } from '@/shared/hooks/useIntersection'
import { formatMonthDay } from '@/shared/lib/date'
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

  // 아래로는 미래, 위로는 과거 — 양쪽 끝에 감시자를 둔다(UX §3.11).
  const { ref: topSentinelRef, intersecting: reachedTop } = useIntersection()
  const { ref: bottomSentinelRef, intersecting: reachedEnd } = useIntersection()

  const { loadPast, loadFuture } = calendar
  useEffect(() => {
    if (reachedEnd) loadFuture()
  }, [reachedEnd, loadFuture])
  useEffect(() => {
    if (reachedTop) loadPast()
  }, [reachedTop, loadPast])

  const target = calendar.carryTarget

  return (
    <>
      <SummaryStats summary={summaryQuery.data} isLoading={summaryQuery.isPending} />

      <nav className="flex gap-4 py-4" aria-label={landmarks.adminNav}>
        <TextLink to={paths.adminStats}>{screens.admin.statsLink}</TextLink>
        <TextLink to={paths.adminMembers}>{screens.admin.membersLink}</TextLink>
        <TextLink to={paths.adminSettings}>{screens.admin.settingsLink}</TextLink>
      </nav>

      {calendar.query.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 7 }, (_, index) => (
            <Skeleton key={index} className="h-control-lg w-full" />
          ))}
        </div>
      ) : calendar.query.isError ? (
        <ErrorState
          message={resolveErrorMessage(calendar.query.error)}
          onRetry={() => void calendar.query.refetch()}
        />
      ) : (
        <>
          {/* 위쪽 감시자 — 과거 30일을 이어 받는다(PRD GAP-7). */}
          {calendar.hasMorePast ? <div ref={topSentinelRef} className="py-2" /> : null}
          {calendar.loadingPast ? <Skeleton className="h-control-lg w-full" /> : null}

          <ul className="list-none p-0">
            {calendar.days.map((day) => (
              <DayRow key={day.date} day={day} onCarryDraft={calendar.setCarryTarget} />
            ))}
          </ul>
        </>
      )}

      <div ref={bottomSentinelRef} className="py-4" />

      <BackLink to={paths.landing} label={actions.backHome} />

      {/* 이어쓰기 확인 — 이동이지 복사가 아니다. 원본 날짜는 비워진다. */}
      <Dialog
        open={Boolean(target)}
        title={target ? screens.admin.carryDialogTitle(formatMonthDay(target.date)) : ''}
        description={
          target
            ? // 문구는 `8월 31일` 꼴이다(UX §3.11 예시). `08.31 일`이 아니다.
              screens.admin.carryDialogBody(
                target.draftProgress.artworkCount,
                formatMonthDay(target.date),
                calendar.todayDate ? formatMonthDay(calendar.todayDate) : '',
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

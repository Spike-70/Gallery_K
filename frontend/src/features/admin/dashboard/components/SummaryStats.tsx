import type { AdminSummary } from '@/entities/exhibition/model/admin'
import { screens, status } from '@/shared/config/messages'
import { Skeleton } from '@/shared/ui'

/**
 * 요약 줄 — UX 설계서 §3.11
 * PRD 부록 B가 지정한 두 숫자만 보여준다. 연장이 2일 이상이면 조용한 안내를 덧붙인다 —
 * **경고색·느낌표를 쓰지 않는다**(RISK-1).
 */
export type SummaryStatsProps = {
  summary: AdminSummary | undefined
  isLoading: boolean
}

export function SummaryStats({ summary, isLoading }: SummaryStatsProps) {
  if (isLoading) return <Skeleton className="h-5 w-2/3" />
  // 요약 줄만 실패해도 목록은 정상 렌더한다(UX §3.11).
  if (!summary) return null

  return (
    <div className="flex flex-col gap-1">
      <p className="tabular text-body-md text-primary">
        {screens.admin.summaryEntrants(summary.todayEntrantCount)} ·{' '}
        {screens.admin.summaryWeekly(summary.weeklyActiveRatio)}
      </p>
      {summary.carriedOverDays >= 2 ? (
        <p className="text-body-sm text-tertiary">{status.carryoverNoticeAdmin}</p>
      ) : null}
    </div>
  )
}

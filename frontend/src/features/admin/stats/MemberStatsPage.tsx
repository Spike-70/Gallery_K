import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { fetchMemberStats } from '@/features/admin/stats/api/statsApi'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { actions, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { formatShortDate } from '@/shared/lib/date'
import type { Uuid } from '@/shared/types/utility'
import { BackLink, ErrorState, Skeleton } from '@/shared/ui'

/**
 * B-1-1. 사용자별 감상 상세 *(v1.1)* — UX 설계서 §3.17
 *
 * **개인정보 문구를 화면 하단에 상시 표시한다.** 가입 시 안내한 범위를 넘지 않도록
 * 보는 사람에게 스스로 상기시키는 장치다(PRD §6.11).
 */
export function MemberStatsPage() {
  const { memberId } = useParams<{ memberId: Uuid }>()

  const query = useQuery({
    queryKey: ['admin', 'stats', 'member', memberId, 30],
    queryFn: () => fetchMemberStats(memberId as Uuid, 30),
    enabled: Boolean(memberId),
    ...CACHE_POLICY.stats,
  })

  if (query.isPending) return <Skeleton className="h-12 w-full" lines={8} />
  if (query.isError) {
    return <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
  }

  return (
    <>
      <h1 className="pb-6 text-title-md text-primary">{query.data.member.name}</h1>

      <ul className="list-none p-0">
        {query.data.days.map((day) => (
          <li key={day.date} className="flex items-center justify-between border-b border-border-default py-3">
            <span className="tabular text-body-md text-primary">
              {formatShortDate(day.date)} · {day.exhibitionTitle ?? '—'}
            </span>
            <span className="tabular text-body-md text-secondary">
              {day.entered ? `${day.viewedArtworkCount} / ${day.totalArtworkCount}` : '—'}
            </span>
          </li>
        ))}
      </ul>

      <p className="py-8 text-caption text-tertiary">{screens.stats.privacyNote}</p>

      <BackLink to={paths.adminStats} label={actions.backPrev} />
    </>
  )
}

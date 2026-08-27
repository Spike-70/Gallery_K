import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { statsKeys } from '@/features/admin/stats/api/keys'
import { fetchDailyStats, searchMembers } from '@/features/admin/stats/api/statsApi'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { actions, screenTitles, screens, status, templates } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue'
import { formatShortDate } from '@/shared/lib/date'
import { BackLink, EmptyState, ErrorState, FieldGroup, Skeleton, TextField } from '@/shared/ui'

/**
 * B-1. 관람 현황 *(v1.1)* — UX 설계서 §3.17
 * 최근 7일 목록 + 회원 검색. 연장된 날은 제목 앞에 `↑`를 둔다.
 */
export function StatsPage() {
  const [search, setSearch] = useState('')
  const debounced = useDebouncedValue(search, 300)

  const dailyQuery = useQuery({
    queryKey: statsKeys.daily(),
    queryFn: fetchDailyStats,
    ...CACHE_POLICY.stats,
  })

  const memberQuery = useQuery({
    queryKey: statsKeys.memberSearch(debounced),
    queryFn: () => searchMembers(debounced),
    enabled: debounced.length > 0,
    ...CACHE_POLICY.stats,
  })

  return (
    <>
      <h1 className="pb-6 text-title-md text-primary">{screenTitles.adminStats}</h1>

      {dailyQuery.isPending ? (
        <Skeleton className="h-12 w-full" lines={5} />
      ) : dailyQuery.isError ? (
        <ErrorState message={resolveErrorMessage(dailyQuery.error)} onRetry={() => void dailyQuery.refetch()} />
      ) : dailyQuery.data.length === 0 ? (
        <EmptyState message={status.statsEmpty} icon="calendar" />
      ) : (
        <ul className="list-none p-0">
          {dailyQuery.data.map((day) => (
            <li key={day.date} className="flex items-center justify-between border-b border-border-default py-3">
              <span className="tabular text-body-md text-primary">
                {formatShortDate(day.date)} ·{' '}
                {day.exhibitionTitle
                  ? day.isCarriedOver
                    ? templates.carriedOverTitle(day.exhibitionTitle)
                    : day.exhibitionTitle
                  : templates.none}
              </span>
              <span className="tabular text-body-md text-secondary">
                {templates.entrantCount(day.entrantCount)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="py-8">
        <FieldGroup id="stats-search" label={screens.stats.searchLabel}>
          <TextField
            id="stats-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={screens.members.searchPlaceholder}
          />
        </FieldGroup>

        {memberQuery.data && memberQuery.data.length > 0 ? (
          <ul className="list-none p-0 pt-3">
            {memberQuery.data.map((member) => (
              <li key={member.id} className="border-b border-border-default">
                <Link
                  to={paths.adminMemberStats(member.id)}
                  className="flex min-h-touch items-center justify-between py-2"
                >
                  <span className="text-body-md text-primary">{member.name}</span>
                  <span className="tabular text-caption text-tertiary">{member.phoneMasked}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <BackLink to={paths.admin} label={actions.backAdmin} />
    </>
  )
}

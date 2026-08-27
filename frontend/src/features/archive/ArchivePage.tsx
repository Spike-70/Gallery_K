import { useEffect, useRef } from 'react'

import { useArchiveQuery } from '@/entities/exhibition/api/queries'
import { ArchiveRow } from '@/entities/exhibition/ui/ArchiveRow'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screenTitles, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useIntersection } from '@/shared/hooks/useIntersection'
import { BackLink, EmptyState, ErrorState, Skeleton } from '@/shared/ui'

/**
 * C-3. 지난 전시 — UX 설계서 §3.9
 *
 * 최근 30개에서 **끝난다.** 마지막에 `여기까지입니다`를 조용히 표시한다(UX-2).
 * 감상 표식은 배지가 아니라 제목 색 낮춤으로만 나타낸다 — 재촉하지 않는다(UX-5).
 */
export function ArchivePage() {
  const query = useArchiveQuery()
  const sentinelRef = useRef<HTMLDivElement>(null)
  const reachedEnd = useIntersection(sentinelRef)

  useEffect(() => {
    if (reachedEnd && query.hasNextPage && !query.isFetchingNextPage) {
      void query.fetchNextPage()
    }
  }, [reachedEnd, query])

  const exhibitions = query.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <>
      <h1 className="pb-6 text-center text-title-md text-primary">{screenTitles.archive}</h1>

      {query.isPending ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-[72px] w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : exhibitions.length === 0 ? (
        <EmptyState message={status.archiveEmpty} icon="calendar" />
      ) : (
        <>
          <ul className="list-none p-0">
            {exhibitions.map((exhibition) => (
              <li key={exhibition.date}>
                <ArchiveRow exhibition={exhibition} to={paths.archiveDate(exhibition.date)} />
              </li>
            ))}
          </ul>

          <div ref={sentinelRef} className="py-6 text-center">
            {query.hasNextPage ? (
              <Skeleton className="mx-auto h-4 w-24" />
            ) : (
              <p className="text-caption text-tertiary">{status.archiveEnd}</p>
            )}
          </div>
        </>
      )}

      <BackLink to={paths.gallery} label={actions.backGallery} />
    </>
  )
}

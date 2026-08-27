import {
  useCurrentExhibitionQuery,
  useExhibitionByDateQuery,
} from '@/entities/exhibition/api/queries'
import { useGalleryContext } from '@/entities/exhibition/model/useGalleryContext'
import { DateLine } from '@/entities/exhibition/ui/DateLine'
import { ExhibitionTitle } from '@/entities/exhibition/ui/ExhibitionTitle'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { formatFullDate } from '@/shared/lib/date'
import { BackLink, ErrorState, Skeleton } from '@/shared/ui'

/**
 * C-1. 전시 테마 — UX 설계서 §3.7
 *
 * 본문은 `container-reading`(480px) 안에서 조판하고 **원문 줄바꿈을 보존**한다.
 * `dangerouslySetInnerHTML`을 쓰지 않고 CSS `white-space: pre-line`으로 처리한다(§12).
 *
 * 작가 목록은 라벨 없이 명단만 `·`로 연결한다.
 */
export function ExhibitionThemePage() {
  const context = useGalleryContext()
  const isArchive = context.mode === 'archive'

  const currentQuery = useCurrentExhibitionQuery(!isArchive)
  const archiveQuery = useExhibitionByDateQuery(isArchive ? (context.date ?? undefined) : undefined)
  const query = isArchive ? archiveQuery : currentQuery

  if (query.isPending) {
    return (
      <div className="gk-container-reading flex flex-col items-center gap-4">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="mt-4 h-4 w-full" lines={6} />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <>
        <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
        <BackLink to={context.galleryPath} label={context.backToGalleryLabel} />
      </>
    )
  }

  const exhibition = query.data

  return (
    <div className="gk-container-reading">
      <header className="flex flex-col items-center gap-2 pb-8">
        <DateLine label={formatFullDate(exhibition.viewingDate)} />
        <ExhibitionTitle title={exhibition.title} carriedOverLabel={exhibition.carriedOverLabel} />
      </header>

      <p className="gk-prose">{exhibition.theme}</p>

      {exhibition.artists.length > 0 ? (
        <p className="mt-8 text-caption text-tertiary">{exhibition.artists.join(' · ')}</p>
      ) : null}

      <BackLink to={context.galleryPath} label={context.backToGalleryLabel} />
    </div>
  )
}

import { useParams } from 'react-router-dom'

import { useExhibitionPreviewQuery } from '@/entities/exhibition/api/adminQueries'
// 관람자 기능의 **공개 표면**만 참조한다. 미리보기가 관람자 화면과 픽셀 단위로 같아야
// 하므로 컴포넌트를 복제하지 않는다(프런트 §8.4, PRD §5.3 4단계).
import { GalleryView } from '@/features/gallery'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { formatShortDate } from '@/shared/lib/date'
import type { IsoDate } from '@/shared/types/utility'
import { ErrorState, LinkButton, Skeleton } from '@/shared/ui'

/**
 * 미리보기 — UX 설계서 §3.18
 *
 * 데스크톱에서는 **390px 폭 모바일 프레임** 안에 렌더하고, 상단 바는 **프레임 바깥**에 둔다.
 *
 * `GalleryView`는 데이터를 프롭으로만 받는 순수 컴포넌트이므로, 이 화면은 컨테이너
 * 계층에 붙어 있는 `viewTracker`를 자연히 타지 않는다 — **기록이 전송되지 않는다.**
 * 별도 플래그로 억제하지 않는 것이 이 분리의 이점이다.
 */
export function PreviewPage() {
  const { date } = useParams<{ date: IsoDate }>()
  const query = useExhibitionPreviewQuery(date)

  if (!date) return null

  return (
    <div className="min-h-screen bg-subtle">
      <header className="flex items-center justify-between border-b border-border-default bg-surface px-4 py-3">
        <span className="tabular text-body-md text-primary">
          {screenTitles.preview} · {formatShortDate(date)}
        </span>
        <LinkButton to={paths.adminExhibition(date)} variant="ghost" size="sm">
          {actions.close}
        </LinkButton>
      </header>

      <div className="flex justify-center py-6">
        <div className="w-full max-w-preview bg-canvas px-4 py-6 sm:border sm:border-border-default">
          {query.isPending ? (
            <Skeleton className="h-6 w-full" lines={8} />
          ) : query.isError || !query.data ? (
            <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
          ) : (
            <GalleryView
              exhibition={query.data}
              themeTo={paths.adminExhibitionTheme(date)}
              artworkPath={() => paths.adminExhibitionPreview(date)}
            />
          )}
        </div>
      </div>

      <p className="pb-8 text-center text-caption text-tertiary">{screens.editor.previewIncompleteNote}</p>
    </div>
  )
}

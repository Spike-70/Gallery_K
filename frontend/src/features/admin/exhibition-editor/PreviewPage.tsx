import { useMemo } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import type { ArtworkDetail } from '@/entities/artwork/model/types'
import {
  useAdminExhibitionQuery,
  useExhibitionPreviewQuery,
} from '@/entities/exhibition/api/adminQueries'
import { DateLine } from '@/entities/exhibition/ui/DateLine'
import { ExhibitionTitle } from '@/entities/exhibition/ui/ExhibitionTitle'
import { ArtworkArticle } from '@/entities/artwork/ui/ArtworkArticle'
// 관람자 기능의 **공개 표면**만 참조한다. 미리보기가 관람자 화면과 픽셀 단위로 같아야
// 하므로 컴포넌트를 복제하지 않는다(프런트 §8.4, PRD §5.3 4단계).
import { GalleryView } from '@/features/gallery'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { formatFullDate, formatShortDate } from '@/shared/lib/date'
import type { IsoDate } from '@/shared/types/utility'
import { BackLink, ErrorState, LinkButton, Skeleton } from '@/shared/ui'

/**
 * 미리보기 — UX 설계서 §3.18
 *
 * 데스크톱에서는 **390px 폭 모바일 프레임** 안에 렌더하고, 상단 바는 **프레임 바깥**에 둔다.
 *
 * **미리보기 안에서 전시 테마·그림 화면까지 실제로 이동할 수 있다.** 이동 상태는 쿼리
 * 파라미터가 갖는다 — 별도 라우트를 파면 관람자 경로와 관리자 경로가 두 벌이 된다.
 *
 * `GalleryView`·`ArtworkArticle`은 데이터를 프롭으로만 받는 순수 컴포넌트이므로, 이 화면은
 * 컨테이너 계층에 붙어 있는 `viewTracker`를 자연히 타지 않는다 — **기록이 전송되지 않는다.**
 * 별도 플래그로 억제하지 않는 것이 이 분리의 이점이다.
 */
type PreviewView = 'gallery' | 'theme' | 'artwork'

export function PreviewPage() {
  const { date } = useParams<{ date: IsoDate }>()
  const [searchParams] = useSearchParams()

  const view = (searchParams.get('view') ?? 'gallery') as PreviewView
  const position = Number(searchParams.get('position') ?? '0')

  const query = useExhibitionPreviewQuery(date)
  // 그림 본문(설명·연도·출처)은 미리보기 응답에 없다. 편집 중인 원고에서 가져온다.
  const draftQuery = useAdminExhibitionQuery(date)

  /** 관람자가 볼 그림 한 점 — 미리보기 이미지 + 편집 중 원고를 합친다. */
  const artwork = useMemo<ArtworkDetail | null>(() => {
    const exhibition = query.data
    const slot = draftQuery.data?.slots.find((candidate) => candidate.position === position)
    if (!exhibition || !slot) return null
    const summary = exhibition.artworks.find((candidate) => candidate.position === position)
    if (!summary) return null
    return {
      ...summary,
      yearText: slot.yearText ?? '',
      description: slot.description ?? '',
      collection: slot.collection,
      sourceUrl: slot.sourceUrl,
      prevArtworkId: null,
      nextArtworkId: null,
    }
  }, [query.data, draftQuery.data, position])

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
          ) : view === 'theme' ? (
            <div className="gk-container-reading">
              <header className="flex flex-col items-center gap-2 pb-8">
                <DateLine label={formatFullDate(query.data.viewingDate)} />
                <ExhibitionTitle title={query.data.title} carriedOverLabel={null} />
              </header>
              <p className="gk-prose">{query.data.theme}</p>
              {query.data.artists.length > 0 ? (
                <p className="mt-8 text-caption text-tertiary">{query.data.artists.join(' · ')}</p>
              ) : null}
              <BackLink to={paths.adminExhibitionPreview(date)} label={actions.backGallery} />
            </div>
          ) : view === 'artwork' && artwork ? (
            <>
              <ArtworkArticle artwork={artwork} />
              <BackLink to={paths.adminExhibitionPreview(date)} label={actions.backGallery} />
            </>
          ) : (
            <GalleryView
              exhibition={query.data}
              themeTo={`${paths.adminExhibitionPreview(date)}?view=theme`}
              artworkPath={(artworkId) => {
                const slot = query.data.artworks.find((candidate) => candidate.id === artworkId)
                return `${paths.adminExhibitionPreview(date)}?view=artwork&position=${slot?.position ?? 1}`
              }}
              // 아직 올라오지 않은 자리는 `준비 중`으로 그린다(API §9.12, UX §3.18).
              pendingLabel={screens.editor.previewIncomplete}
            />
          )}
        </div>
      </div>

      <p className="pb-8 text-center text-caption text-tertiary">{screens.editor.previewIncompleteNote}</p>
    </div>
  )
}

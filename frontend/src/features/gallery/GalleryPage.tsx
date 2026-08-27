import { Link } from 'react-router-dom'

import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { ArtworkGridSkeleton } from '@/features/gallery/components/ArtworkGrid'
import { GalleryFooterNav } from '@/features/gallery/components/GalleryFooterNav'
import { GalleryView } from '@/features/gallery/components/GalleryView'
import { useGalleryExhibition } from '@/features/gallery/hooks/useGalleryExhibition'
import { useScrollRestoration } from '@/shared/hooks/useScrollRestoration'
import { actions, screens, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import {
  Banner,
  BackLinkGroup,
  EmptyState,
  ErrorState,
  PullToRefresh,
  Skeleton,
  TextLink,
} from '@/shared/ui'

/**
 * C. 갤러리 — 중심 화면(UX 설계서 §3.6)
 *
 * 페이지의 골격은 셋이다: **(1) 데이터 훅 → (2) 상태 분기 → (3) 표현 컴포넌트 조합**(프런트 §8.1).
 * 상태 분기를 하위 컴포넌트에 위임하지 않는다.
 */
export function GalleryPage() {
  const { context, query, exhibition, prefetchArtwork } = useGalleryExhibition()

  // C → C-2 → 뒤로가기에서 보고 있던 자리로 돌아온다(§8.3).
  useScrollRestoration(context.mode === 'archive' ? `archive:${context.date}` : 'gallery')


  if (query.isPending) {
    return (
      <>
        <div className="flex flex-col items-center gap-2 pb-6">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-8 w-2/3" />
        </div>
        <ArtworkGridSkeleton />
      </>
    )
  }

  if (query.isError) {
    // 개관 전은 오류가 아니라 빈 상태다(UX §11).
    if (isApiError(query.error) && query.error.code === ERROR_CODES.exhibitionNotOpened) {
      return (
        <>
          <EmptyState message={status.firstExhibitionPending} />
          <div className="flex justify-center">
            <TextLink to={paths.landing}>{actions.backHome}</TextLink>
          </div>
        </>
      )
    }

    if (isApiError(query.error) && query.error.code === ERROR_CODES.exhibitionNotFound) {
      return (
        <>
          <ErrorState message={screens.errors.exhibitionNotFoundTitle} />
          <div className="flex justify-center">
            <TextLink to={paths.gallery}>{actions.backGallery}</TextLink>
          </div>
        </>
      )
    }

    // 실패해도 **되돌아갈 길은 남긴다**(UX-3). 화면에 갇히게 두지 않는다.
    return (
      <>
        <ErrorState
          message={resolveErrorMessage(query.error) || status.exhibitionLoadFailed}
          onRetry={() => void query.refetch()}
          requestId={isApiError(query.error) ? query.error.requestId : null}
        />
        {context.mode === 'archive' ? (
          <BackLinkGroup
            links={[
              { to: paths.archive, label: actions.backArchive },
              { to: paths.gallery, label: actions.todayExhibition },
            ]}
          />
        ) : (
          <GalleryFooterNav />
        )}
      </>
    )
  }

  if (!exhibition) return null

  return (
    // 당겨서 새로고침(UX §7). 대체 수단은 오류 상태의 `다시 시도` 버튼이다.
    <PullToRefresh onRefresh={() => query.refetch()} disabled={query.isFetching}>
      {/* 아카이브 모드에서만 상단 안내 바를 얹는다(PRD §6.8). */}
      {context.mode === 'archive' ? (
        <Banner
          tone="info"
          message={status.archiveBanner}
          className="-mx-4 mb-4 sm:-mx-6"
          action={
            <Link to={paths.gallery} className="min-h-touch text-body-sm text-accent underline underline-offset-4">
              {actions.todayExhibition}
            </Link>
          }
        />
      ) : null}

      <GalleryView
        exhibition={exhibition}
        themeTo={context.themePath}
        artworkPath={context.artworkPath}
        onPrefetch={prefetchArtwork}
        onRetryImage={() => void query.refetch()}
      />

      {context.mode === 'archive' ? (
        <BackLinkGroup
          links={[
            { to: paths.archive, label: actions.backArchive },
            { to: paths.gallery, label: actions.todayExhibition },
          ]}
        />
      ) : (
        <GalleryFooterNav />
      )}
    </PullToRefresh>
  )
}

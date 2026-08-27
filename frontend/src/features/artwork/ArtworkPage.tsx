import { useParams } from 'react-router-dom'

import { useArtworkQuery, useCachedArtwork } from '@/entities/artwork/api/queries'
import { PositionIndicator } from '@/entities/artwork/ui/PositionIndicator'
import { ArtworkArticle } from '@/entities/artwork/ui/ArtworkArticle'
import { ImmersiveViewer } from '@/features/artwork/components/ImmersiveViewer'
import { SwipePager } from '@/features/artwork/components/SwipePager'
import { useArtworkNavigation } from '@/features/artwork/hooks/useArtworkNavigation'
import { useArtworkViewLog } from '@/features/artwork/hooks/useArtworkViewLog'
import { useViewerStore } from '@/features/artwork/model/viewerStore'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, landmarks } from '@/shared/config/messages'
import { BackLink, ErrorState, Skeleton, TextLink } from '@/shared/ui'
import type { Uuid } from '@/shared/types/utility'

/**
 * C-2. 그림 — UX 설계서 §3.8
 *
 * **텍스트가 그림 위에 온다.** 스크롤 없이 제목·작가·설명이 먼저 보이고 그림은 그 아래에서
 * 충분한 크기로 나타난다. 그림을 먼저 두면 설명을 보려고 매번 스크롤해야 한다(U-1).
 *
 * 되돌아가기 대상은 문맥이 결정한다 — 아카이브에서 열었으면 `이 전시로`(F-14).
 */
export function ArtworkPage() {
  const { artworkId } = useParams<{ artworkId: Uuid }>()
  const query = useArtworkQuery(artworkId)
  const view = query.data

  const { context, prevId, nextId, goPrev, goNext } = useArtworkNavigation(view)

  // 프리페치된 이웃이 있으면 스와이프 중 따라 들어온다(UX §3.8). 없으면 조용히 생략한다.
  const prevArtwork = useCachedArtwork(prevId)
  const nextArtwork = useCachedArtwork(nextId)
  useArtworkViewLog(artworkId)

  const viewerOpen = useViewerStore((state) => state.open)
  const openViewer = useViewerStore((state) => state.open_)
  const closeViewer = useViewerStore((state) => state.close)

  if (query.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-4 w-full" lines={4} />
        <Skeleton className="aspect-[4/5] w-full" />
      </div>
    )
  }

  if (query.isError || !view) {
    return (
      <>
        <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
        <BackLink to={context.galleryPath} label={context.backToGalleryLabel} />
      </>
    )
  }

  const { artwork } = view

  return (
    <>
      <SwipePager
        canGoPrev={Boolean(prevId)}
        canGoNext={Boolean(nextId)}
        onPrev={goPrev}
        onNext={goNext}
        prevPeek={prevArtwork ? <ArtworkArticle artwork={prevArtwork.artwork} /> : null}
        nextPeek={nextArtwork ? <ArtworkArticle artwork={nextArtwork.artwork} /> : null}
      >
        <ArtworkArticle
          artwork={artwork}
          onOpenViewer={() => openViewer(artwork.id)}
          onRetryImage={() => void query.refetch()}
        />
      </SwipePager>

      <PositionIndicator label={view.positionLabel} className="pt-6" />

      {/* 스와이프의 대체 수단 — 텍스트 링크(UX-7). `크게 보기`는 그림 우하단에만 둔다(UX §3.8). */}
      <nav className="flex items-center justify-between pt-2" aria-label={landmarks.artworkNav}>
        {prevId ? (
          <TextLink to={context.artworkPath(prevId)}>{actions.prevArtwork}</TextLink>
        ) : (
          <span aria-hidden />
        )}
        {nextId ? (
          <TextLink to={context.artworkPath(nextId)}>{actions.nextArtwork}</TextLink>
        ) : (
          <span aria-hidden />
        )}
      </nav>

      <BackLink to={context.galleryPath} label={context.backToGalleryLabel} />

      {viewerOpen ? <ImmersiveViewer artwork={artwork} onClose={closeViewer} /> : null}
    </>
  )
}

import { useParams } from 'react-router-dom'

import { useArtworkQuery } from '@/entities/artwork/api/queries'
import { PositionIndicator } from '@/entities/artwork/ui/PositionIndicator'
import { ArtworkFrame } from '@/features/artwork/components/ArtworkFrame'
import { ImmersiveViewer } from '@/features/artwork/components/ImmersiveViewer'
import { SwipePager } from '@/features/artwork/components/SwipePager'
import { useArtworkNavigation } from '@/features/artwork/hooks/useArtworkNavigation'
import { useArtworkViewLog } from '@/features/artwork/hooks/useArtworkViewLog'
import { useViewerStore } from '@/features/artwork/model/viewerStore'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screens } from '@/shared/config/messages'
import { BackLink, ErrorState, Skeleton, TextButton, TextLink } from '@/shared/ui'
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
  useArtworkViewLog(artworkId)

  const viewerOpen = useViewerStore((state) => state.open)
  const openViewer = useViewerStore((state) => state.open_)
  const closeViewer = useViewerStore((state) => state.close)

  if (query.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-28" />
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
      <SwipePager canGoPrev={Boolean(prevId)} canGoNext={Boolean(nextId)} onPrev={goPrev} onNext={goNext}>
        <article className="flex flex-col gap-3">
          <h1 className="text-title-md text-primary">{artwork.title}</h1>
          <p className="text-caption text-tertiary">
            {artwork.artist}
            {artwork.yearText ? `, ${artwork.yearText}` : ''}
          </p>

          {/* 설명은 원문 줄바꿈을 보존한다(§4.3). */}
          <p className="gk-prose">{artwork.description}</p>

          <ArtworkFrame
            artwork={artwork}
            onOpenViewer={() => openViewer(artwork.id)}
            onRetry={() => void query.refetch()}
          />

          {artwork.collection || artwork.sourceUrl ? (
            <p className="text-caption text-tertiary">
              {artwork.collection}
              {artwork.collection && artwork.sourceUrl ? ' · ' : ''}
              {artwork.sourceUrl ? (
                <a
                  href={artwork.sourceUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline underline-offset-4"
                >
                  {screens.artwork.sourceLabel}
                </a>
              ) : null}
            </p>
          ) : null}
        </article>
      </SwipePager>

      <PositionIndicator label={view.positionLabel} className="pt-6" />

      {/* 스와이프의 대체 수단 — 텍스트 링크(UX-7) */}
      <nav className="flex items-center justify-between pt-2" aria-label="그림 이동">
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

      <div className="flex justify-center pt-4">
        <TextButton tone="tertiary" onClick={() => openViewer(artwork.id)}>
          {actions.viewLarge}
        </TextButton>
      </div>

      <BackLink to={context.galleryPath} label={context.backToGalleryLabel} />

      {viewerOpen ? <ImmersiveViewer artwork={artwork} onClose={closeViewer} /> : null}
    </>
  )
}

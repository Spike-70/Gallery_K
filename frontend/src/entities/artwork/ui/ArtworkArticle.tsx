import type { ArtworkDetail } from '@/entities/artwork/model/types'
import { ArtworkFrame } from '@/entities/artwork/ui/ArtworkFrame'
import { screens } from '@/shared/config/messages'

/**
 * 그림 한 점의 본문 — UX 설계서 §3.8
 *
 * **텍스트가 그림 위에 온다.** 스크롤 없이 제목·작가·설명이 먼저 보이고 그림은 그 아래에서
 * 충분한 크기로 나타난다(U-1).
 *
 * 현재 그림과 **스와이프 중 따라 들어오는 이웃 그림**, 그리고 **관리자 미리보기**가
 * 같은 컴포넌트를 쓴다 — 그래야 "그림만 바뀌고 설명은 그대로"인 상태가 한순간도 생기지 않고,
 * 미리보기가 관람자 화면과 어긋나지 않는다(UX §3.8·§3.18).
 *
 * 도메인 타입을 받는 순수 표현 컴포넌트이므로 `entities`에 산다(프런트 §4.2).
 */
export type ArtworkArticleProps = {
  artwork: ArtworkDetail
  onOpenViewer?: () => void
  onRetryImage?: () => void
}

export function ArtworkArticle({ artwork, onOpenViewer, onRetryImage }: ArtworkArticleProps) {
  return (
    <article className="flex flex-col gap-3">
      <h1 className="text-title-md text-primary">{artwork.title}</h1>
      <p className="text-caption text-tertiary">
        {artwork.artist}
        {artwork.yearText ? `, ${artwork.yearText}` : ''}
      </p>

      {/* 설명은 원문 줄바꿈을 보존한다(§4.3). */}
      <p className="gk-prose">{artwork.description}</p>

      <ArtworkFrame artwork={artwork} onOpenViewer={onOpenViewer} onRetry={onRetryImage} />

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
  )
}

import { memo } from 'react'
import { Link } from 'react-router-dom'

import { ArtworkImage } from '@/entities/artwork/ui/ArtworkImage'
import { type ArtworkSummary, artworkAltText } from '@/entities/artwork/model/types'
import { cn } from '@/shared/lib/cn'

/**
 * ArtworkThumb — 디자인 시스템 문서 §8.2
 *
 * 정사각 크롭 + 작가명 + 열람 표식. 제목은 표시하지 않는다(UX §3.6).
 * 열람 표식은 우상단 4px 점이며 **아주 옅게** 둔다 — 재촉하지 않는다(UX-5).
 *
 * 12개뿐이라 가상화하지 않는다. 대신 `memo`로 개별 리렌더를 차단한다(프런트 §9.5).
 */
export type ArtworkThumbProps = {
  artwork: ArtworkSummary
  to: string
  priority?: boolean
  onPrefetch?: () => void
  /** 이미지가 실패한 칸에 재시도 수단을 준다. 나머지 칸은 정상 렌더된다(UX §3.6). */
  onRetryImage?: () => void
  /** 아직 올라오지 않은 자리의 문구(미리보기) */
  pendingLabel?: string
}

export const ArtworkThumb = memo(function ArtworkThumb({
  artwork,
  to,
  priority,
  onPrefetch,
  onRetryImage,
  pendingLabel,
}: ArtworkThumbProps) {
  return (
    <Link
      to={to}
      onPointerDown={onPrefetch}
      className={cn('group flex flex-col gap-1 focus-visible:outline-offset-4')}
    >
      <div className="relative">
        <ArtworkImage
          image={artwork.image}
          alt={artworkAltText(artwork)}
          variant="thumb"
          priority={priority}
          onRetry={onRetryImage}
          pendingLabel={pendingLabel}
        />
        {artwork.isViewed ? (
          <span
            aria-hidden
            className="absolute right-1 top-1 h-1 w-1 rounded-full bg-tertiary opacity-40"
          />
        ) : null}
      </div>
      <span className="truncate text-caption text-tertiary">{artwork.artist}</span>
    </Link>
  )
})

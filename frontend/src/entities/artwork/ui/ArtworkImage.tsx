import { useState } from 'react'

import type { ImageSet } from '@/entities/artwork/model/types'
import { actions, status } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/Button'

/**
 * ArtworkImage — 이미지 표현 규격(디자인 시스템 문서 §9)
 *
 * - 종횡비를 예약해 레이아웃 시프트를 0으로 만든다.
 * - LQIP data URL을 배경으로 깔고 로드 완료 시 페이드인한다. **확대/축소 효과는 쓰지 않는다** —
 *   작품을 왜곡하는 인상을 준다(§6 규칙 2).
 * - 실패하면 **이미지 영역만** 대체하고 텍스트는 유지한다(PRD §6.7).
 * - 저장 방지를 하지 않는다. `user-select`·컨텍스트 메뉴를 막지 않는다.
 *
 * 인라인 `style`은 종횡비·LQIP에 한해 허용된다(디자인 시스템 §11.4).
 */
export type ArtworkImageProps = {
  image: ImageSet | null
  alt: string
  /** `thumb`는 정사각 크롭, `display`는 원본 비율 */
  variant?: 'thumb' | 'display'
  /** 상위 6개는 즉시 로드한다(§9.2) */
  priority?: boolean
  className?: string
  onRetry?: () => void
}

export function ArtworkImage({
  image,
  alt,
  variant = 'display',
  priority = false,
  className,
  onRetry,
}: ArtworkImageProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  const src = image ? (variant === 'thumb' ? image.thumbUrl : image.displayUrl) : null
  const aspectRatio = variant === 'thumb' ? 1 : (image?.aspectRatio ?? 4 / 5)

  if (!src || failed) {
    return (
      <div
        className={cn('flex flex-col items-center justify-center gap-3 bg-subtle', className)}
        style={{ aspectRatio }}
      >
        <p className="text-caption text-tertiary">{status.imageLoadFailed}</p>
        {onRetry ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setFailed(false)
              onRetry()
            }}
          >
            {actions.retry}
          </Button>
        ) : null}
      </div>
    )
  }

  return (
    <div
      className={cn('relative overflow-hidden bg-subtle', className)}
      style={{
        aspectRatio,
        backgroundImage: image?.lqip ? `url("${image.lqip}")` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      <img
        src={src}
        alt={alt}
        width={image?.width ?? undefined}
        height={image?.height ?? undefined}
        loading={priority ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : 'auto'}
        decoding="async"
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        className={cn(
          'h-full w-full transition-opacity duration-fast ease-standard',
          variant === 'thumb' ? 'object-cover' : 'object-contain',
          loaded ? 'opacity-100' : 'opacity-0',
        )}
      />
    </div>
  )
}

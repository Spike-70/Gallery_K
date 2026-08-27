import { useState } from 'react'

import type { ImageSet } from '@/entities/artwork/model/types'
import { reportImageFailure, reportImageSuccess } from '@/entities/artwork/model/imageRecovery'
import { actions, status } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/Button'
import { Icon } from '@/shared/ui/Icon'
import { IconButton } from '@/shared/ui/IconButton'

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
  /**
   * 이미지가 **아직 없는** 자리에 쓸 문구(미리보기의 `준비 중` 등).
   * 없는 것과 실패한 것은 다르다 — 실패에만 재시도를 붙인다.
   */
  pendingLabel?: string
}

export function ArtworkImage({
  image,
  alt,
  variant = 'display',
  priority = false,
  className,
  onRetry,
  pendingLabel,
}: ArtworkImageProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  const src = image ? (variant === 'thumb' ? image.thumbUrl : image.displayUrl) : null
  const aspectRatio = variant === 'thumb' ? 1 : (image?.aspectRatio ?? 4 / 5)

  const retry = () => {
    setFailed(false)
    onRetry?.()
  }

  // 아직 올라오지 않은 자리 — 오류가 아니므로 재시도를 권하지 않는다(API §9.12).
  if (!src && pendingLabel) {
    return (
      <div
        className={cn('flex items-center justify-center bg-subtle', className)}
        style={{ aspectRatio }}
      >
        <span className="text-caption text-tertiary">{pendingLabel}</span>
      </div>
    )
  }

  if (!src || failed) {
    /**
     * 썸네일은 80px 남짓의 정사각이다. 본문 문구와 버튼을 그대로 넣으면 칸이 깨진다.
     * **회색 칸 + 재시도 아이콘**으로 줄이고 이름은 `aria-label`이 전달한다(UX §3.6).
     */
    if (variant === 'thumb') {
      return (
        <div className={cn('flex items-center justify-center bg-subtle', className)} style={{ aspectRatio }}>
          {onRetry ? (
            <IconButton icon="refresh" label={actions.retry} iconSize="sm" onClick={retry} />
          ) : (
            <Icon name="image" size="md" className="text-tertiary" />
          )}
        </div>
      )
    }

    return (
      <div
        className={cn('flex flex-col items-center justify-center gap-3 bg-subtle', className)}
        style={{ aspectRatio }}
      >
        <p className="text-caption text-tertiary">{status.imageLoadFailed}</p>
        {onRetry ? (
          <Button variant="secondary" size="sm" onClick={retry}>
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
        onLoad={() => {
          setLoaded(true)
          reportImageSuccess()
        }}
        onError={() => {
          // 서명 쿠키 만료면 전부가 403이다. 복구가 시작됐으면 한 번 더 걸어 본다(F-12).
          if (reportImageFailure()) {
            window.setTimeout(() => setFailed(false), 800)
          }
          setFailed(true)
        }}
        className={cn(
          'h-full w-full transition-opacity duration-fast ease-standard',
          variant === 'thumb' ? 'object-cover' : 'object-contain',
          loaded ? 'opacity-100' : 'opacity-0',
        )}
      />
    </div>
  )
}

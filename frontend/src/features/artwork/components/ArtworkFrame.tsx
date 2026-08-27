import type { ArtworkDetail } from '@/entities/artwork/model/types'
import { artworkAltText } from '@/entities/artwork/model/types'
import { ArtworkImage } from '@/entities/artwork/ui/ArtworkImage'
import { actions } from '@/shared/config/messages'
import { Button, Icon } from '@/shared/ui'

/**
 * ArtworkFrame — 디자인 시스템 문서 §8.2
 *
 * 원본 비율 이미지 + 우하단 `크게 보기` 버튼. 종횡비를 예약해 레이아웃 시프트가 0이다.
 * 버튼은 **핀치 제스처를 모르는 사용자를 위한 상시 노출 대체 수단**이다(PRD §5.2).
 */
export type ArtworkFrameProps = {
  artwork: ArtworkDetail
  onOpenViewer: () => void
  onRetry?: () => void
}

export function ArtworkFrame({ artwork, onOpenViewer, onRetry }: ArtworkFrameProps) {
  return (
    <figure className="relative m-0">
      <button
        type="button"
        onClick={onOpenViewer}
        aria-label={`${artworkAltText(artwork)} — ${actions.viewLarge}`}
        className="block w-full"
      >
        <ArtworkImage image={artwork.image} alt={artworkAltText(artwork)} onRetry={onRetry} />
      </button>

      <div className="absolute bottom-2 right-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={onOpenViewer}
          leading={<Icon name="zoom-in" size="sm" />}
        >
          {actions.viewLarge}
        </Button>
      </div>
    </figure>
  )
}

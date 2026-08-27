import type { ArtworkSummary } from '@/entities/artwork/model/types'
import { ArtworkThumb } from '@/entities/artwork/ui/ArtworkThumb'
import { EAGER_IMAGE_COUNT } from '@/shared/config/constants'
import type { Uuid } from '@/shared/types/utility'

/**
 * 그림 그리드 — 디자인 시스템 문서 §5.3 · 프런트엔드 §9.2
 *
 * 3열 × 4행(큰 글씨 2열 × 6행). **열 수 전환은 `data-font-scale` 하나로 일어난다** —
 * 이 컴포넌트에 분기가 없다.
 *
 * 상위 6개는 즉시 로드하고 나머지는 지연 로드한다. `ul`/`li` + 링크로 시맨틱을 갖춘다(§11).
 */
export type ArtworkGridProps = {
  artworks: ArtworkSummary[]
  artworkPath: (artworkId: Uuid) => string
  onPrefetch?: (artworkId: Uuid) => void
}

export function ArtworkGrid({ artworks, artworkPath, onPrefetch }: ArtworkGridProps) {
  return (
    <ul className="gk-artwork-grid list-none p-0">
      {artworks.map((artwork, index) => (
        <li key={artwork.id}>
          <ArtworkThumb
            artwork={artwork}
            to={artworkPath(artwork.id)}
            priority={index < EAGER_IMAGE_COUNT}
            onPrefetch={onPrefetch ? () => onPrefetch(artwork.id) : undefined}
          />
        </li>
      ))}
    </ul>
  )
}

/** 로딩 자리 — 12개 회색 정사각(UX §3.6) */
export function ArtworkGridSkeleton() {
  return (
    <div className="gk-artwork-grid" aria-hidden>
      {Array.from({ length: 12 }, (_, index) => (
        <div key={index} className="gk-shimmer aspect-square" />
      ))}
    </div>
  )
}

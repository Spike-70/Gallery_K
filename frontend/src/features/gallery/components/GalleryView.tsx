import type { Exhibition } from '@/entities/exhibition/model/types'
import { ArtworkGrid } from '@/features/gallery/components/ArtworkGrid'
import { ExhibitionHeader } from '@/features/gallery/components/ExhibitionHeader'
import type { Uuid } from '@/shared/types/utility'

/**
 * 갤러리 표현 컴포넌트 — 프런트엔드 아키텍처 문서 §8.4
 *
 * **데이터를 프롭으로만 받는 순수 컴포넌트**다. 데이터를 가져오는 일은 컨테이너
 * (`GalleryPage`)가 한다. 이 분리 덕분에 관리자 미리보기가 같은 화면을 그대로 재사용하고,
 * 기록 전송 경로를 타지 않는다.
 */
export type GalleryViewProps = {
  exhibition: Exhibition
  themeTo: string
  artworkPath: (artworkId: Uuid) => string
  onPrefetch?: (artworkId: Uuid) => void
}

export function GalleryView({ exhibition, themeTo, artworkPath, onPrefetch }: GalleryViewProps) {
  return (
    <>
      <ExhibitionHeader
        viewingDate={exhibition.viewingDate}
        title={exhibition.title}
        carriedOverLabel={exhibition.carriedOverLabel}
        themeTo={themeTo}
      />
      <ArtworkGrid artworks={exhibition.artworks} artworkPath={artworkPath} onPrefetch={onPrefetch} />
    </>
  )
}

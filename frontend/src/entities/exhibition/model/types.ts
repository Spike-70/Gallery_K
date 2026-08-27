import type { ArtworkSummary, ImageSet } from '@/entities/artwork/model/types'
import type { IsoDate } from '@/shared/types/utility'

/**
 * 전시 도메인 타입 — API 명세서 §3.4·§3.5
 *
 * `entities/exhibition`은 `entities/artwork`를 참조한다. 전시는 그림을 담는 개념이므로
 * 이 방향의 의존은 자연스럽고 순환하지 않는다(프런트 §4.1).
 */
export type Exhibition = {
  /** **발행일** */
  date: IsoDate
  title: string
  /** 500자 이내. 줄바꿈을 보존해 표시한다 */
  theme: string
  /** 중복 제거된 작가 목록. C-1 하단용 */
  artists: string[]
  artworks: ArtworkSummary[]
  /** **관람일**. 서버 기준 오늘 */
  viewingDate: IsoDate
  isCarriedOver: boolean
  /** 연장 시에만 `8월 30일의 전시`. **서버가 완성된 문구로 준다** */
  carriedOverLabel: string | null
  isArchiveView: boolean
}

export type ExhibitionSummary = {
  date: IsoDate
  title: string
  coverImage: ImageSet | null
  artworkCount: number
  viewedArtworkCount: number
  isViewed: boolean
}

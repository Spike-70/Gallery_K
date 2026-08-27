import type { Uuid } from '@/shared/types/utility'

/** 그림 이미지 3종 — API 명세서 §3.1 */
export type ImageSet = {
  /** 400×400 WebP. C 그리드용 */
  thumbUrl: string
  /** 긴 변 1600px WebP. C-2용 */
  displayUrl: string
  /** 원본. **전체 화면 확대 요청 시에만** 사용한다 */
  originUrl: string | null
  /** 16px 폭 블러 플레이스홀더(추가 요청 0) */
  lqip: string | null
  width: number | null
  height: number | null
  /** 레이아웃 시프트 방지용. CLS 목표는 0이다 */
  aspectRatio: number | null
}

export type ArtworkSummary = {
  id: Uuid
  /** 1–12 */
  position: number
  /** C 그리드에는 작가명만 노출한다(PRD §6.5) */
  artist: string
  /** 대체 텍스트 구성용. 그리드에 시각적으로 표시하지 않는다 */
  title: string
  image: ImageSet
  /** 이 회원이 **이 전시에서** 이미 열어봤는지 */
  isViewed: boolean
}

export type ArtworkDetail = ArtworkSummary & {
  yearText: string
  description: string
  collection: string | null
  sourceUrl: string | null
  prevArtworkId: Uuid | null
  nextArtworkId: Uuid | null
}

/** C-2 화면이 한 번의 조회로 완성되도록 전시 문맥을 함께 담는다(API 문서 §7.5) */
export type ArtworkView = {
  artwork: ArtworkDetail
  exhibition: {
    date: string
    title: string
    isCarriedOver: boolean
    carriedOverLabel: string | null
  }
  /** `3 / 12` — 서버가 완성한 문자열 */
  positionLabel: string
}

/** 대체 텍스트는 `{제목} – {작가}` (PRD §8.3) */
export function artworkAltText(artwork: Pick<ArtworkSummary, 'title' | 'artist'>): string {
  return `${artwork.title} – ${artwork.artist}`
}

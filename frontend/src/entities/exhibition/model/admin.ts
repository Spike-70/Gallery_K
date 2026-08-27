import type { ImageSet } from '@/entities/artwork/model/types'
import type { EditMode, ExhibitionDayStatus, ImageStatus } from '@/shared/types/enums'
import type { IsoDate, IsoDateTime, Uuid } from '@/shared/types/utility'

/** 관리자 달력 행 — API 명세서 §3.9 */
export type AdminExhibitionDay = {
  date: IsoDate
  status: ExhibitionDayStatus
  title: string | null
  carriedFromDate: IsoDate | null
  carriedFromTitle: string | null
  hasDraft: boolean
  draftProgress: {
    artworkCount: number
    completeArtworkCount: number
    hasTitle: boolean
    hasTheme: boolean
  }
  isHidden: boolean
  isEditable: boolean
  /** **서버가 결정한다.** 백필 금지·이어쓰기 조건은 도메인 규칙이다 */
  editMode: EditMode
  isToday: boolean
  updatedAt: IsoDateTime | null
}

/** 편집 슬롯 — API 명세서 §9.3. 항상 12개가 온다. */
export type AdminSlot = {
  position: number
  artworkId: Uuid | null
  title: string | null
  artist: string | null
  yearText: string | null
  description: string | null
  collection: string | null
  sourceUrl: string | null
  imageStatus: ImageStatus
  image: ImageSet | null
  imageErrorCode: string | null
  isComplete: boolean
  version: number | null
}

export type AdminExhibition = {
  date: IsoDate
  title: string | null
  theme: string | null
  isPublished: boolean
  publishedAt: IsoDateTime | null
  isHidden: boolean
  editMode: EditMode
  canPublish: boolean
  /** `missing_title` | `missing_theme` | `incomplete_artwork:{position}` */
  publishBlockers: string[]
  slots: AdminSlot[]
  /** 낙관적 잠금 토큰 */
  version: number
  draftUpdatedAt: IsoDateTime | null
  carryDraftSource: { fromDate: IsoDate; artworkCount: number } | null
}

export type AdminSummary = {
  todayEntrantCount: number
  weeklyActiveRatio: number
  weeklyActiveCount: number
  totalMemberCount: number
  /** 오늘 기준 연속 연장 일수. 0이면 오늘 발행됨 */
  carriedOverDays: number
  pendingDraftCount: number
  leadTimeDays: number
}

/**
 * `SlotButton`의 시각 상태 5종 — 디자인 시스템 문서 §8.3
 * 서버 `image_status` 4종에 **메타데이터 완성 여부**가 곱해져 5종이 된다(S-9).
 */
export type SlotVisualState = 'empty' | 'uploading' | 'incomplete' | 'complete' | 'failed'

export function slotVisualState(slot: AdminSlot): SlotVisualState {
  switch (slot.imageStatus) {
    case 'empty':
      return 'empty'
    case 'uploading':
      return 'uploading'
    case 'failed':
      return 'failed'
    case 'ready':
      return slot.isComplete ? 'complete' : 'incomplete'
  }
}

/** 발행 조건 안내 문구를 만들기 위한 분해 — `발행까지 — 그림 3점, 전시 테마` */
export function summarizeBlockers(blockers: string[]): { missingArtworks: number; missingTitle: boolean; missingTheme: boolean } {
  return {
    missingArtworks: blockers.filter((code) => code.startsWith('incomplete_artwork')).length,
    missingTitle: blockers.includes('missing_title'),
    missingTheme: blockers.includes('missing_theme'),
  }
}

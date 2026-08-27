import type { Notice } from '@/entities/notice/model/types'
import type { IsoDate } from '@/shared/types/utility'

/**
 * A 첫 화면 통합 조회 결과 — API 명세서 §6.1
 * 화면 진입당 왕복 1회 원칙(AP-3)에 따라 제목·공지·가입 가능 여부·관리자 여부를 한 번에 받는다.
 */
export type Landing = {
  today: IsoDate
  /** `2026. 08. 27. 목` — 서버가 완성한 표시 문자열 */
  todayLabel: string
  exhibitionTitle: string | null
  hasExhibition: boolean
  notice: Notice | null
  signupOpen: boolean
  isAuthenticated: boolean
  /** true일 때만 `Curator K` 링크를 렌더한다 */
  isCurator: boolean
  memberName: string | null
}

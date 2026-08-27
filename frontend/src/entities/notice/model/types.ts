import type { IsoDate, Uuid } from '@/shared/types/utility'

/** 휴관 공지 — API 명세서 §3.7 */
export type Notice = {
  id: Uuid
  startsOn: IsoDate
  endsOn: IsoDate
  /** 최대 300자 */
  body: string
  isActive: boolean
}

import type { CreatedVia, PushPlatform, PushStatus, UserRole } from '@/shared/types/enums'
import type { IsoDate, IsoDateTime, TimeOfDay, Uuid } from '@/shared/types/utility'

/**
 * 회원(관리자 전용) — API 명세서 §3.8
 * **관리자 응답에서만 전체 전화번호가 온다.** B-3은 전화 한 통으로 돕는 화면이다.
 */
export type Member = {
  id: Uuid
  name: string
  phone: string
  role: UserRole
  createdAt: IsoDateTime
  createdVia: CreatedVia
  isBlocked: boolean
  blockedAt: IsoDateTime | null
  notifyEnabled: boolean
  notifyAt: TimeOfDay
  /** 구독은 있는데 발송이 실패 중이면 `inactive` */
  pushStatus: PushStatus
  /** iOS 안내가 필요한 회원을 식별한다(PRD §6.14) */
  pushPlatforms: PushPlatform[]
  lastLoginAt: IsoDateTime | null
  lastViewedOn: IsoDate | null
}

/** 홈 화면 추가 안내가 필요한 회원인가 — K가 전화로 도울 대상(U-6) */
export function needsIosGuide(member: Member): boolean {
  return member.pushStatus === 'none' && member.pushPlatforms.includes('ios')
}

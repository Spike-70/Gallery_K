import type { FontScale, UserRole } from '@/shared/types/enums'
import type { IsoDateTime, TimeOfDay, Uuid } from '@/shared/types/utility'

/** 도메인 타입(camelCase) — 서버 원형과의 변환은 `api/mappers.ts`에서만 일어난다. */
export type SessionUser = {
  id: Uuid
  name: string
  /** `010-****-5678` — 전체 전화번호는 어떤 관람자 API에서도 오지 않는다 */
  phoneMasked: string
  role: UserRole
  fontScale: FontScale
  notifyEnabled: boolean
  notifyAt: TimeOfDay
  /** true면 비밀번호 변경 화면으로 강제 이동한다(대행 가입·초기화된 계정) */
  mustChangePassword: boolean
  createdAt: IsoDateTime
}

export type Session = {
  isAuthenticated: boolean
  user: SessionUser | null
  /** 만료 10분 전에 미디어 쿠키를 갱신한다(프런트 §8.2 F-12) */
  mediaSessionExpiresAt: IsoDateTime | null
}

export function isCurator(user: SessionUser | null): boolean {
  return user?.role === 'curator'
}

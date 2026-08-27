import type { FontScale, SocialProvider, UserRole } from '@/shared/types/enums'
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
  /**
   * false면 **소셜로만 로그인하는 계정**이다(소셜 문서 §5.2).
   * D 설정 화면이 비밀번호 변경 항목을 감춘다 — 없는 비밀번호를 바꾸라고 하지 않는다.
   */
  hasPassword: boolean
  createdAt: IsoDateTime
}

/** 연결된 외부 계정 — API 명세서 §3.10 */
export type SocialIdentity = {
  id: Uuid
  provider: SocialProvider
  /** 화면에 그대로 쓰는 한국어 이름. 서버가 준다 */
  label: string
  email: string | null
  displayName: string | null
  linkedAt: IsoDateTime
  lastLoginAt: IsoDateTime | null
}

/** A-1·D의 소셜 버튼 한 칸 — API 명세서 §6.11 */
export type SocialProviderOption = {
  provider: SocialProvider
  label: string
  /** `<a href>`가 그대로 쓰는 절대 경로 */
  startUrl: string
}

export type Session = {
  isAuthenticated: boolean
  user: SessionUser | null
}

export function isCurator(user: SessionUser | null): boolean {
  return user?.role === 'curator'
}

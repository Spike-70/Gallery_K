import type {
  RawSession,
  RawSessionUser,
  RawSocialIdentity,
  RawSocialProvider,
} from '@/shared/api/types'

import type {
  Session,
  SessionUser,
  SocialIdentity,
  SocialProviderOption,
} from '@/entities/session/model/types'

/**
 * 서버 원형 → 도메인 변환.
 * 이 변환을 두는 이유는 명명 통일이 아니라 **API 변경의 파급 차단**이다(프런트 §7.4).
 */
export function toSessionUser(raw: RawSessionUser): SessionUser {
  return {
    id: raw.id,
    name: raw.name,
    phoneMasked: raw.phone_masked,
    role: raw.role,
    fontScale: raw.font_scale,
    notifyEnabled: raw.notify_enabled,
    notifyAt: raw.notify_at,
    mustChangePassword: raw.must_change_password,
    hasPassword: raw.has_password,
    createdAt: raw.created_at,
  }
}

export function toSocialIdentity(raw: RawSocialIdentity): SocialIdentity {
  return {
    id: raw.id,
    provider: raw.provider,
    label: raw.label,
    email: raw.email,
    displayName: raw.display_name,
    linkedAt: raw.linked_at,
    lastLoginAt: raw.last_login_at,
  }
}

export function toSocialProviderOption(raw: RawSocialProvider): SocialProviderOption {
  return { provider: raw.provider, label: raw.label, startUrl: raw.start_url }
}

export function toSession(raw: RawSession): Session {
  return {
    isAuthenticated: raw.is_authenticated,
    user: raw.user ? toSessionUser(raw.user) : null,
  }
}

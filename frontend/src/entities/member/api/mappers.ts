import type { RawMemberItem } from '@/shared/api/types'

import type { Member } from '@/entities/member/model/types'

export function toMember(raw: RawMemberItem): Member {
  return {
    id: raw.id,
    name: raw.name,
    phone: raw.phone,
    role: raw.role,
    createdAt: raw.created_at,
    createdVia: raw.created_via,
    isBlocked: raw.is_blocked,
    blockedAt: raw.blocked_at,
    notifyEnabled: raw.notify_enabled,
    notifyAt: raw.notify_at,
    pushStatus: raw.push_status,
    pushPlatforms: raw.push_platforms,
    lastLoginAt: raw.last_login_at,
    lastViewedOn: raw.last_viewed_on,
  }
}

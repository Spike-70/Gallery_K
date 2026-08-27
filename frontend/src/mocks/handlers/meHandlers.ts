import { ERROR_CODES } from '@/shared/api/ApiError'
import type { RawPushSubscription, RawSessionUser } from '@/shared/api/types'
import type { FontScale, PushPlatform } from '@/shared/types/enums'
import type { Uuid } from '@/shared/types/utility'

import { db, nowIso, uuid } from '@/mocks/db'
import { mockDelay, mockFail } from '@/mocks/lib/mockClient'
import { memberFontScale, requireMember, toSessionUser } from '@/mocks/lib/serializers'

/** `GET /me` — API 명세서 §8.1 */
export function getMe(): Promise<{ user: RawSessionUser }> {
  const member = requireMember()
  return mockDelay({ user: toSessionUser(member) }, 160)
}

/** `PATCH /me/settings` — 보낸 필드만 반영한다. 빈 바디는 거부한다. */
export async function updateSettings(input: {
  notifyEnabled?: boolean
  notifyAt?: string
  fontScale?: FontScale
}): Promise<{ user: RawSessionUser }> {
  const member = requireMember()
  if (input.notifyEnabled === undefined && input.notifyAt === undefined && input.fontScale === undefined) {
    mockFail(ERROR_CODES.validationFailed, 422)
  }

  if (input.notifyEnabled !== undefined) {
    member.notify_enabled = input.notifyEnabled
    member.push_status = input.notifyEnabled ? 'active' : 'none'
  }
  if (input.notifyAt !== undefined) member.notify_at = input.notifyAt
  if (input.fontScale !== undefined) memberFontScale.set(member.id, input.fontScale)

  return mockDelay({ user: toSessionUser(member) }, 240)
}

/** `DELETE /me` — 큐레이터 계정은 탈퇴할 수 없다 */
export async function withdraw(): Promise<Record<string, never>> {
  const member = requireMember()
  if (member.role === 'curator') {
    mockFail(ERROR_CODES.memberCuratorImmutable, 403)
  }
  await mockDelay(null, 420)
  db.members = db.members.filter((candidate) => candidate.id !== member.id)
  db.currentUserId = null
  db.viewedArtworks.clear()
  return {}
}

/** `GET /me/push-subscriptions` — 부팅 시 브라우저 구독과 대조하기 위한 목록 */
export function listPushSubscriptions(): Promise<{ subscriptions: RawPushSubscription[] }> {
  requireMember()
  return mockDelay({ subscriptions: db.pushSubscriptions }, 140)
}

/** `POST /me/push-subscriptions` — 권한 허용이 곧 알림을 켜겠다는 의사표시다 */
export async function registerPushSubscription(input: {
  endpointHash: string
  platform: PushPlatform
}): Promise<{ subscription_id: Uuid; is_new: boolean }> {
  const member = requireMember()
  const existing = db.pushSubscriptions.find((item) => item.endpoint_hash === input.endpointHash)
  if (existing) {
    return mockDelay({ subscription_id: existing.id, is_new: false }, 200)
  }

  const created: RawPushSubscription = {
    id: uuid(`ps${db.pushSubscriptions.length}`, db.pushSubscriptions.length),
    endpoint_hash: input.endpointHash,
    platform: input.platform,
    is_active: true,
    created_at: nowIso(),
    last_success_at: null,
  }
  db.pushSubscriptions.push(created)
  member.notify_enabled = true
  member.push_status = 'active'
  return mockDelay({ subscription_id: created.id, is_new: true }, 260)
}

/** `DELETE /me/push-subscriptions/{id}` — `notify_enabled`는 건드리지 않는다 */
export async function deletePushSubscription(id: Uuid): Promise<Record<string, never>> {
  requireMember()
  db.pushSubscriptions = db.pushSubscriptions.filter((item) => item.id !== id)
  return mockDelay({}, 160)
}

import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawPushSubscription } from '@/shared/api/types'
import type { PushPlatform } from '@/shared/types/enums'
import type { Uuid } from '@/shared/types/utility'

export type ServerSubscription = {
  id: Uuid
  endpointHash: string
  platform: PushPlatform
  isActive: boolean
}

/** `GET /me/push-subscriptions` — 부팅당 1회 대조용(프런트 §10.3) */
export async function fetchPushSubscriptions(): Promise<ServerSubscription[]> {
  const raw = await httpClient.get<{ subscriptions: RawPushSubscription[] }>(
    endpoints.me.pushSubscriptions(),
  )

  return raw.subscriptions.map((subscription) => ({
    id: subscription.id,
    endpointHash: subscription.endpoint_hash,
    platform: subscription.platform,
    isActive: subscription.is_active,
  }))
}

/**
 * `POST /me/push-subscriptions` — 등록 성공 시 서버가 `notify_enabled`도 켠다.
 * endpoint 원문과 암호화 키가 있어야 서버가 발송할 수 있다(API 문서 §8.5).
 */
export async function registerPushSubscription(input: {
  endpoint: string
  keys: { p256dh: string; auth: string }
  platform: PushPlatform
}): Promise<Uuid> {
  const raw = await httpClient.post<{ subscription_id: Uuid; is_new: boolean }>(
    endpoints.me.pushSubscriptions(),
    { endpoint: input.endpoint, keys: input.keys, platform: input.platform },
  )
  return raw.subscription_id
}

/** `DELETE /me/push-subscriptions/{id}` — 해당 단말 구독만 해제한다 */
export async function deletePushSubscription(id: Uuid): Promise<void> {
  await httpClient.delete(endpoints.me.pushSubscription(id))
}

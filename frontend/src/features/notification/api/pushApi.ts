// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
import type { PushPlatform } from '@/shared/types/enums'
import type { Uuid } from '@/shared/types/utility'

// [MOCK]
import * as meMock from '@/mocks/handlers/meHandlers'

export type ServerSubscription = {
  id: Uuid
  endpointHash: string
  platform: PushPlatform
  isActive: boolean
}

/** `GET /me/push-subscriptions` — 부팅당 1회 대조용(프런트 §10.3) */
export async function fetchPushSubscriptions(): Promise<ServerSubscription[]> {
  // [API]
  // const raw = await httpClient.get<{ subscriptions: RawPushSubscription[] }>(
  //   endpoints.me.pushSubscriptions(),
  // )

  // [MOCK]
  const raw = await meMock.listPushSubscriptions()

  return raw.subscriptions.map((subscription) => ({
    id: subscription.id,
    endpointHash: subscription.endpoint_hash,
    platform: subscription.platform,
    isActive: subscription.is_active,
  }))
}

/** `POST /me/push-subscriptions` — 등록 성공 시 서버가 `notify_enabled`도 켠다 */
export async function registerPushSubscription(input: {
  endpointHash: string
  platform: PushPlatform
}): Promise<Uuid> {
  // [API]
  // const raw = await httpClient.post<{ subscription_id: string; is_new: boolean }>(
  //   endpoints.me.pushSubscriptions(),
  //   { endpoint: input.endpointHash, keys: { p256dh: '...', auth: '...' }, platform: input.platform },
  // )
  // return raw.subscription_id

  // [MOCK]
  const raw = await meMock.registerPushSubscription(input)
  return raw.subscription_id
}

/** `DELETE /me/push-subscriptions/{id}` — 해당 단말 구독만 해제한다 */
export async function deletePushSubscription(id: Uuid): Promise<void> {
  // [API]
  // await httpClient.delete(endpoints.me.pushSubscription(id))

  // [MOCK]
  await meMock.deletePushSubscription(id)
}

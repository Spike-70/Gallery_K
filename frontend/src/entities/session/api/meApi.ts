// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import type { RawSessionUser } from '@/shared/api/types'
import type { FontScale } from '@/shared/types/enums'
import type { TimeOfDay } from '@/shared/types/utility'

import { toSessionUser } from '@/entities/session/api/mappers'
import type { SessionUser } from '@/entities/session/model/types'

// [MOCK]
import * as meMock from '@/mocks/handlers/meHandlers'

export type SettingsPatch = {
  notifyEnabled?: boolean
  notifyAt?: TimeOfDay
  fontScale?: FontScale
}

/** `PATCH /me/settings` — 보낸 필드만 반영된다. 빈 바디는 서버가 거부한다. */
export async function updateSettings(patch: SettingsPatch): Promise<SessionUser> {
  // [API]
  // const raw = await httpClient.patch<{ user: RawSessionUser }>(endpoints.me.settings(), {
  //   notify_enabled: patch.notifyEnabled,
  //   notify_at: patch.notifyAt,
  //   font_scale: patch.fontScale,
  // })
  // return toSessionUser(raw.user)

  // [MOCK]
  const raw = await meMock.updateSettings(patch)
  return toSessionUser(raw.user)
}

/** `DELETE /me` — 명시적 확인 필드를 요구한다(API 문서 §8.3) */
export async function withdraw(): Promise<void> {
  // [API]
  // await httpClient.delete(endpoints.me.root(), { confirm: true })

  // [MOCK]
  await meMock.withdraw()
}

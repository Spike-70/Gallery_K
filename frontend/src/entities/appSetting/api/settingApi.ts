// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import type { RawAppSetting } from '@/shared/api/types'

import type { AppSetting } from '@/entities/appSetting/model/types'

// [MOCK]
import * as adminMock from '@/mocks/handlers/adminHandlers'

function toSetting(raw: {
  key: string
  value: string | number | boolean
  value_type: 'string' | 'number' | 'boolean'
  description: string
  is_mutable: boolean
  updated_at: string | null
}): AppSetting {
  return {
    key: raw.key,
    value: raw.value,
    valueType: raw.value_type,
    description: raw.description,
    isMutable: raw.is_mutable,
    updatedAt: raw.updated_at,
  }
}

/** `GET /admin/settings` */
export async function fetchSettings(): Promise<AppSetting[]> {
  // [API]
  // const raw = await httpClient.get<{ settings: RawAppSetting[] }>(endpoints.admin.settings())
  // return raw.settings.map(toSetting)

  // [MOCK]
  const raw = await adminMock.getAdminSettings()
  return raw.settings.map(toSetting)
}

/** `PATCH /admin/settings` — 변경할 키만 담아 보내고 전체를 돌려받는다 */
export async function updateSettings(
  values: Record<string, string | number | boolean>,
): Promise<AppSetting[]> {
  // [API]
  // const raw = await httpClient.patch<{ settings: RawAppSetting[] }>(endpoints.admin.settings(), {
  //   settings: values,
  // })
  // return raw.settings.map(toSetting)

  // [MOCK]
  const raw = await adminMock.updateAdminSettings(values)
  return raw.settings.map(toSetting)
}

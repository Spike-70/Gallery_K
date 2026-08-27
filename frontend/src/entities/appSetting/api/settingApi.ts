import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawAppSetting } from '@/shared/api/types'

import type { AppSetting } from '@/entities/appSetting/model/types'

function toSetting(raw: RawAppSetting): AppSetting {
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
  const raw = await httpClient.get<{ settings: RawAppSetting[] }>(endpoints.admin.settings())
  return raw.settings.map(toSetting)
}

/** `PATCH /admin/settings` — 변경할 키만 담아 보내고 전체를 돌려받는다 */
export async function updateSettings(
  values: Record<string, string | number | boolean>,
): Promise<AppSetting[]> {
  const raw = await httpClient.patch<{ settings: RawAppSetting[] }>(endpoints.admin.settings(), {
    settings: values,
  })
  return raw.settings.map(toSetting)
}

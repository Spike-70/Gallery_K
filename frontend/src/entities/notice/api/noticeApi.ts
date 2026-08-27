// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import type { RawNoticeItem } from '@/shared/api/types'
import type { IsoDate, Uuid } from '@/shared/types/utility'

import { toNotice } from '@/entities/notice/api/mappers'
import type { Notice } from '@/entities/notice/model/types'

// [MOCK]
import * as adminMock from '@/mocks/handlers/adminHandlers'

/** `GET /admin/notices` */
export async function fetchNotices(includePast = false): Promise<Notice[]> {
  // [API]
  // const raw = await httpClient.get<{ notices: RawNoticeItem[] }>(endpoints.admin.notices(), {
  //   query: { include_past: includePast },
  // })
  // return raw.notices.map(toNotice)

  // [MOCK]
  const raw = await adminMock.getNotices(includePast)
  return raw.notices.map(toNotice)
}

/** `POST /admin/notices` — 기간이 겹치면 `NOTICE_PERIOD_OVERLAP` */
export async function createNotice(input: {
  startsOn: IsoDate
  endsOn: IsoDate
  body: string
}): Promise<Notice> {
  // [API]
  // const raw = await httpClient.post<{ notice: RawNoticeItem }>(endpoints.admin.notices(), {
  //   starts_on: input.startsOn,
  //   ends_on: input.endsOn,
  //   body: input.body,
  // })
  // return toNotice(raw.notice)

  // [MOCK]
  const raw = await adminMock.createNotice(input)
  return toNotice(raw.notice)
}

/** `DELETE /admin/notices/{id}` — 실제로는 `is_active=false` 처리다 */
export async function deleteNotice(id: Uuid): Promise<void> {
  // [API]
  // await httpClient.delete(endpoints.admin.notice(id))

  // [MOCK]
  await adminMock.deleteNotice(id)
}

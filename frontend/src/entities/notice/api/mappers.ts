import type { RawNoticeItem } from '@/shared/api/types'

import type { Notice } from '@/entities/notice/model/types'

export function toNotice(raw: RawNoticeItem): Notice {
  return {
    id: raw.id,
    startsOn: raw.starts_on,
    endsOn: raw.ends_on,
    body: raw.body,
    isActive: raw.is_active,
  }
}

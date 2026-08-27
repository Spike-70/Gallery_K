import type { RawLanding, RawNoticeItem } from '@/shared/api/types'
import { formatFullDate } from '@/shared/lib/date'

import { currentExhibition, currentMember, db, getSetting } from '@/mocks/db'
import { mockDelay } from '@/mocks/lib/mockClient'

/** 오늘 유효한 휴관 공지 하나 (API 문서 §6.1 `notice`) */
function activeNotice(): RawNoticeItem | null {
  return (
    db.notices.find(
      (notice) => notice.is_active && notice.starts_on <= db.today && notice.ends_on >= db.today,
    ) ?? null
  )
}

/**
 * `GET /public/landing` — API 명세서 §6.1
 * **이 엔드포인트는 실패하지 않는다.** 목도 같은 계약을 지킨다.
 */
export function getLanding(): Promise<RawLanding> {
  const exhibition = currentExhibition()
  const member = currentMember()
  return mockDelay({
    today: db.today,
    today_label: formatFullDate(db.today),
    exhibition_title: exhibition?.title ?? null,
    has_exhibition: Boolean(exhibition),
    notice: activeNotice(),
    signup_open: getSetting('signup_open', true),
    is_authenticated: Boolean(member),
    is_curator: member?.role === 'curator',
    member_name: member?.name ?? null,
  })
}

/** `GET /public/notice` — API 명세서 §6.2 */
export function getPublicNotice(): Promise<{ notice: RawNoticeItem | null }> {
  return mockDelay({ notice: activeNotice() })
}

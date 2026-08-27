// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import type { RawLanding } from '@/shared/api/types'

import { toNotice } from '@/entities/notice/api/mappers'
import type { Landing } from '@/features/landing/model/types'

// [MOCK]
import * as publicMock from '@/mocks/handlers/publicHandlers'

/**
 * `GET /public/landing`
 * **이 엔드포인트는 실패하지 않는다.** DB 장애 시에도 날짜와 가입 가능 여부만 채워 온다.
 * 화면은 이 응답이 없어도 완전한 레이아웃을 그린다(F-4).
 */
export async function fetchLanding(): Promise<Landing> {
  // [API]
  // const raw = await httpClient.get<RawLanding>(endpoints.public.landing())

  // [MOCK]
  const raw = await publicMock.getLanding()

  return {
    today: raw.today,
    todayLabel: raw.today_label,
    exhibitionTitle: raw.exhibition_title,
    hasExhibition: raw.has_exhibition,
    notice: raw.notice ? toNotice(raw.notice) : null,
    signupOpen: raw.signup_open,
    isAuthenticated: raw.is_authenticated,
    isCurator: raw.is_curator,
    memberName: raw.member_name,
  }
}

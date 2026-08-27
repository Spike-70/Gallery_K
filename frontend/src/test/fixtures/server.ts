import type {
  RawAdminExhibitionDay,
  RawAdminExhibitionDetail,
  RawAdminArtworkSlot,
  RawAdminSummary,
  RawArtworkDetailResponse,
  RawExhibitionDetail,
  RawImageSet,
  RawLanding,
  RawSessionUser,
  RawSocialIdentity,
  RawSocialProvider,
} from '@/shared/api/types'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import type { IsoDate } from '@/shared/types/utility'

/**
 * 서버 원형 응답 픽스처 — 프런트엔드 아키텍처 문서 §14
 *
 * **도메인 타입이 아니라 `Raw*`(snake_case)를 만든다.** 그래야 매퍼가 테스트 경로에서도
 * 함께 검증된다. 날짜는 고정값이다 — 단말 시계를 읽으면 자정 전후로 테스트가 흔들린다.
 */

export const TODAY: IsoDate = '2026-08-28'
export const YESTERDAY: IsoDate = '2026-08-27'
export const TOMORROW: IsoDate = '2026-08-29'
export const EXHIBITION_TITLE = '빛을 등진 사람들'

/** 결정적 UUID. 실제 형식을 지켜야 `parse_uuid` 계열 경로와 같은 값이 흐른다. */
export function artworkId(position: number): string {
  return `00000000-0000-4000-8000-${String(position).padStart(12, '0')}`
}

export function imageSet(position: number): RawImageSet {
  return {
    thumb_url: `https://media.test/thumb/${position}.webp`,
    display_url: `https://media.test/display/${position}.webp`,
    origin_url: null,
    lqip: null,
    width: 1600,
    height: 1200,
    aspect_ratio: 1.3333,
  }
}

/** 이미지가 아직 올라오지 않은 자리 — 미리보기의 미완성 슬롯(API 문서 §9.12) */
export function pendingArtwork(position: number) {
  return { ...artworkSummary(position), image: null }
}

export function artworkSummary(position: number) {
  return {
    id: artworkId(position),
    position,
    artist: `작가 ${position}`,
    title: `그림 ${position}`,
    image: imageSet(position),
    is_viewed: false,
  }
}

export function currentExhibition(
  overrides: Partial<RawExhibitionDetail> = {},
): RawExhibitionDetail {
  return {
    exhibition_date: TODAY,
    title: EXHIBITION_TITLE,
    theme: '역광 속에서도 사람은 사람으로 남는다.',
    artists: Array.from({ length: ARTWORK_COUNT }, (_, index) => `작가 ${index + 1}`),
    artworks: Array.from({ length: ARTWORK_COUNT }, (_, index) => artworkSummary(index + 1)),
    viewing_date: TODAY,
    is_carried_over: false,
    carried_over_label: null,
    is_archive_view: false,
    ...overrides,
  }
}

export function artworkDetail(
  position: number,
  overrides: Partial<RawArtworkDetailResponse['artwork']> = {},
): RawArtworkDetailResponse {
  return {
    artwork: {
      ...artworkSummary(position),
      year_text: '1998',
      description: `그림 ${position}에 대한 설명이다.`,
      collection: null,
      source_url: null,
      prev_artwork_id: position > 1 ? artworkId(position - 1) : null,
      next_artwork_id: position < ARTWORK_COUNT ? artworkId(position + 1) : null,
      ...overrides,
    },
    exhibition: {
      exhibition_date: TODAY,
      title: EXHIBITION_TITLE,
      is_carried_over: false,
      carried_over_label: null,
    },
    position_label: `${position} / ${ARTWORK_COUNT}`,
  }
}

export function landing(overrides: Partial<RawLanding> = {}): RawLanding {
  return {
    today: TODAY,
    today_label: '2026. 08. 28. 금',
    exhibition_title: EXHIBITION_TITLE,
    has_exhibition: true,
    notice: null,
    signup_open: true,
    is_authenticated: false,
    is_curator: false,
    member_name: null,
    ...overrides,
  }
}

export function sessionUser(overrides: Partial<RawSessionUser> = {}): RawSessionUser {
  return {
    id: '00000000-0000-4000-8000-0000000000aa',
    name: '관람객',
    phone_masked: '010-****-5671',
    role: 'viewer',
    font_scale: 'normal',
    notify_enabled: false,
    notify_at: '07:00',
    must_change_password: false,
    has_password: true,
    created_at: '2026-08-01T00:00:00+09:00',
    ...overrides,
  }
}

// ── 관리자 ────────────────────────────────────────────────────────────────

export function adminSummary(overrides: Partial<RawAdminSummary> = {}): RawAdminSummary {
  return {
    today_entrant_count: 14,
    weekly_active_ratio: 62,
    weekly_active_count: 18,
    total_member_count: 29,
    carried_over_days: 0,
    pending_draft_count: 1,
    lead_time_days: 2,
    ...overrides,
  }
}

export function adminDay(
  date: IsoDate,
  overrides: Partial<RawAdminExhibitionDay> = {},
): RawAdminExhibitionDay {
  return {
    date,
    status: 'empty',
    title: null,
    carried_from_date: null,
    carried_from_title: null,
    has_draft: false,
    draft_progress: {
      artwork_count: 0,
      complete_artwork_count: 0,
      has_title: false,
      has_theme: false,
    },
    is_hidden: false,
    is_editable: true,
    edit_mode: 'create',
    is_today: date === TODAY,
    updated_at: null,
    ...overrides,
  }
}

export function emptySlot(position: number): RawAdminArtworkSlot {
  return {
    position,
    artwork_id: null,
    title: null,
    artist: null,
    year_text: null,
    description: null,
    collection: null,
    source_url: null,
    image_status: 'empty',
    image: null,
    image_error_code: null,
    is_complete: false,
    version: null,
  }
}

/** 행이 없어도 서버는 **빈 12슬롯**을 준다(API 문서 §9.3). */
export function adminExhibition(
  date: IsoDate,
  overrides: Partial<RawAdminExhibitionDetail> = {},
): RawAdminExhibitionDetail {
  return {
    exhibition_date: date,
    title: null,
    theme: null,
    is_published: false,
    published_at: null,
    is_hidden: false,
    edit_mode: 'create',
    can_publish: false,
    publish_blockers: [
      'missing_title',
      'missing_theme',
      ...Array.from({ length: ARTWORK_COUNT }, (_, index) => `incomplete_artwork:${index + 1}`),
    ],
    slots: Array.from({ length: ARTWORK_COUNT }, (_, index) => emptySlot(index + 1)),
    version: 0,
    draft_updated_at: null,
    carry_draft_source: null,
    ...overrides,
  }
}

// ── 소셜 로그인 (API 문서 §3.10·§6.11) ─────────────────────────────────────

export function socialProvider(
  overrides: Partial<RawSocialProvider> = {},
): RawSocialProvider {
  const provider = overrides.provider ?? 'kakao'
  return {
    provider,
    label: '카카오',
    // 서버와 같은 규칙으로 파생시킨다 — 픽스처가 경로를 따로 외우지 않는다.
    start_url: `/api/auth/social/${provider}/start`,
    ...overrides,
  }
}

export function socialIdentity(overrides: Partial<RawSocialIdentity> = {}): RawSocialIdentity {
  return {
    id: '00000000-0000-4000-8000-0000000000b1',
    provider: 'kakao',
    label: '카카오',
    email: 'viewer@example.com',
    display_name: '관람자',
    linked_at: '2026-08-20T09:00:00+09:00',
    last_login_at: '2026-08-28T07:10:00+09:00',
    ...overrides,
  }
}

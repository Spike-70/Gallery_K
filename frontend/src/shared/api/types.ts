/**
 * 서버 원형 타입 (snake_case) — API 명세서 §3
 *
 * 이 파일 밖에서는 snake_case를 다루지 않는다. 변환은 각 entity의 `api/` 안에서만
 * 일어나며, 그 이유는 명명 통일이 아니라 **API 변경의 파급 차단**이다(프런트 §7.4).
 */

import type {
  CreatedVia,
  EditMode,
  ExhibitionDayStatus,
  FontScale,
  ImageStatus,
  PushPlatform,
  PushStatus,
  UserRole,
} from '@/shared/types/enums'
import type { IsoDate, IsoDateTime, Nullable, TimeOfDay, Uuid } from '@/shared/types/utility'

/** §3.1 ImageSet */
export type RawImageSet = {
  thumb_url: string
  display_url: string
  origin_url: Nullable<string>
  lqip: Nullable<string>
  width: Nullable<number>
  height: Nullable<number>
  aspect_ratio: Nullable<number>
}

/** §3.2 ArtworkSummary */
export type RawArtworkSummary = {
  id: Uuid
  position: number
  artist: string
  title: string
  image: RawImageSet
  is_viewed: boolean
}

/** §3.3 ArtworkDetail */
export type RawArtworkDetail = RawArtworkSummary & {
  year_text: string
  description: string
  collection: Nullable<string>
  source_url: Nullable<string>
  prev_artwork_id: Nullable<Uuid>
  next_artwork_id: Nullable<Uuid>
}

/** §7.5 그림 상세 응답 */
export type RawArtworkDetailResponse = {
  artwork: RawArtworkDetail
  exhibition: {
    exhibition_date: IsoDate
    title: string
    is_carried_over: boolean
    carried_over_label: Nullable<string>
  }
  position_label: string
}

/** §3.4 ExhibitionSummary */
export type RawExhibitionSummary = {
  exhibition_date: IsoDate
  title: string
  cover_image: Nullable<RawImageSet>
  artwork_count: number
  viewed_artwork_count: number
  is_viewed: boolean
}

/** §3.5 ExhibitionDetail */
export type RawExhibitionDetail = {
  exhibition_date: IsoDate
  title: string
  theme: string
  artists: string[]
  artworks: RawArtworkSummary[]
  viewing_date: IsoDate
  is_carried_over: boolean
  carried_over_label: Nullable<string>
  is_archive_view: boolean
}

/** §3.6 SessionUser */
export type RawSessionUser = {
  id: Uuid
  name: string
  phone_masked: string
  role: UserRole
  font_scale: FontScale
  notify_enabled: boolean
  notify_at: TimeOfDay
  must_change_password: boolean
  created_at: IsoDateTime
}

/** §3.7 NoticeItem */
export type RawNoticeItem = {
  id: Uuid
  starts_on: IsoDate
  ends_on: IsoDate
  body: string
  is_active: boolean
}

/** §3.8 MemberItem */
export type RawMemberItem = {
  id: Uuid
  name: string
  phone: string
  role: UserRole
  created_at: IsoDateTime
  created_via: CreatedVia
  is_blocked: boolean
  blocked_at: Nullable<IsoDateTime>
  notify_enabled: boolean
  notify_at: TimeOfDay
  push_status: PushStatus
  push_platforms: PushPlatform[]
  last_login_at: Nullable<IsoDateTime>
  last_viewed_on: Nullable<IsoDate>
}

/** §3.9 AdminExhibitionDay */
export type RawAdminExhibitionDay = {
  date: IsoDate
  status: ExhibitionDayStatus
  title: Nullable<string>
  carried_from_date: Nullable<IsoDate>
  carried_from_title: Nullable<string>
  has_draft: boolean
  draft_progress: {
    artwork_count: number
    complete_artwork_count: number
    has_title: boolean
    has_theme: boolean
  }
  is_hidden: boolean
  is_editable: boolean
  edit_mode: EditMode
  is_today: boolean
  updated_at: Nullable<IsoDateTime>
}

/** §9.3 AdminArtworkSlot */
export type RawAdminArtworkSlot = {
  position: number
  artwork_id: Nullable<Uuid>
  title: Nullable<string>
  artist: Nullable<string>
  year_text: Nullable<string>
  description: Nullable<string>
  collection: Nullable<string>
  source_url: Nullable<string>
  image_status: ImageStatus
  image: Nullable<RawImageSet>
  image_error_code: Nullable<string>
  is_complete: boolean
  version: Nullable<number>
}

/** §9.3 AdminExhibitionDetail */
export type RawAdminExhibitionDetail = {
  exhibition_date: IsoDate
  title: Nullable<string>
  theme: Nullable<string>
  is_published: boolean
  published_at: Nullable<IsoDateTime>
  is_hidden: boolean
  edit_mode: EditMode
  can_publish: boolean
  publish_blockers: string[]
  slots: RawAdminArtworkSlot[]
  version: number
  draft_updated_at: Nullable<IsoDateTime>
  carry_draft_source: Nullable<{ from_date: IsoDate; artwork_count: number }>
}

/** §9.1 관리자 홈 요약 */
export type RawAdminSummary = {
  today_entrant_count: number
  weekly_active_ratio: number
  weekly_active_count: number
  total_member_count: number
  carried_over_days: number
  pending_draft_count: number
  lead_time_days: number
}

/** §6.1 A 첫 화면 */
export type RawLanding = {
  today: IsoDate
  today_label: string
  exhibition_title: Nullable<string>
  has_exhibition: boolean
  notice: Nullable<RawNoticeItem>
  signup_open: boolean
  is_authenticated: boolean
  is_curator: boolean
  member_name: Nullable<string>
}

/** §6.6 세션 확인 */
export type RawSession = {
  is_authenticated: boolean
  user: Nullable<RawSessionUser>
  media_session_expires_at: Nullable<IsoDateTime>
}

/** §8.5 푸시 구독 */
export type RawPushSubscription = {
  id: Uuid
  endpoint_hash: string
  platform: PushPlatform
  is_active: boolean
  created_at: IsoDateTime
  last_success_at: Nullable<IsoDateTime>
}

/** §9.17 전역 설정 */
export type RawAppSetting = {
  key: string
  value: string | number | boolean
  value_type: 'string' | 'number' | 'boolean'
  description: string
  is_mutable: boolean
  updated_at: Nullable<IsoDateTime>
}

/** §9.19 통계 */
export type RawStatsDay = {
  date: IsoDate
  exhibition_date: Nullable<IsoDate>
  exhibition_title: Nullable<string>
  is_carried_over: boolean
  entrant_count: number
  artwork_view_count: number
}

export type RawMemberStatsDay = {
  date: IsoDate
  exhibition_date: Nullable<IsoDate>
  exhibition_title: Nullable<string>
  entered: boolean
  viewed_artwork_count: number
  total_artwork_count: number
}

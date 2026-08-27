import { ERROR_CODES } from '@/shared/api/ApiError'
import type {
  RawAdminArtworkSlot,
  RawArtworkDetail,
  RawArtworkSummary,
  RawExhibitionDetail,
  RawExhibitionSummary,
  RawMemberItem,
  RawSessionUser,
} from '@/shared/api/types'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { formatMonthDay } from '@/shared/lib/date'
import { maskPhone } from '@/shared/lib/phone'
import type { IsoDate } from '@/shared/types/utility'

import {
  type MockExhibition,
  type MockMember,
  type MockSlot,
  db,
  isViewed,
  slotIsComplete,
  viewedCount,
} from '@/mocks/db'
import { createImageSet } from '@/mocks/lib/imageFactory'
import { mockFail } from '@/mocks/lib/mockClient'

/**
 * 목 상태 → 서버 원형(snake_case) 응답 변환 — 데모 전용
 * **도메인 타입이 아니라 서버 원형을 반환**한다. 그래야 entity의 매퍼가 데모에서도 검증된다.
 */

function imageOf(slot: MockSlot) {
  // 데모에서 큐레이터가 실제로 올린 파일이 있으면 그것을 보여준다.
  if (slot.imageObjectUrl) {
    return {
      thumb_url: slot.imageObjectUrl,
      display_url: slot.imageObjectUrl,
      origin_url: slot.imageObjectUrl,
      lqip: null,
      width: null,
      height: null,
      aspect_ratio: slot.ratio,
    }
  }
  return slot.imageSeed === null ? null : createImageSet(slot.imageSeed, slot.ratio)
}

export function toArtworkSummary(slot: MockSlot, exhibitionDate: IsoDate): RawArtworkSummary {
  return {
    id: slot.artworkId ?? '',
    position: slot.position,
    artist: slot.artist ?? '',
    title: slot.title ?? '',
    image: imageOf(slot) ?? createImageSet(0, slot.ratio),
    is_viewed: isViewed(exhibitionDate, slot.artworkId),
  }
}

export function toArtworkDetail(exhibition: MockExhibition, slot: MockSlot): RawArtworkDetail {
  const ordered = exhibition.slots.filter((candidate) => candidate.artworkId)
  const index = ordered.findIndex((candidate) => candidate.position === slot.position)
  return {
    ...toArtworkSummary(slot, exhibition.date),
    year_text: slot.yearText ?? '',
    description: slot.description ?? '',
    collection: slot.collection,
    source_url: slot.sourceUrl,
    prev_artwork_id: index > 0 ? (ordered[index - 1].artworkId ?? null) : null,
    next_artwork_id: index >= 0 && index < ordered.length - 1 ? (ordered[index + 1].artworkId ?? null) : null,
  }
}

/**
 * `is_carried_over`·`carried_over_label`은 **서버가 계산해서 준다**(API 문서 §3.5).
 * 클라이언트가 날짜를 비교해 문구를 만들면 단말 시계 오차가 UI에 새어 나온다.
 */
export function toExhibitionDetail(
  exhibition: MockExhibition,
  options: { viewingDate: IsoDate; isArchiveView: boolean; includeIncomplete?: boolean },
): RawExhibitionDetail {
  const isCarriedOver = exhibition.date < options.viewingDate && !options.isArchiveView
  const slots = options.includeIncomplete
    ? exhibition.slots
    : exhibition.slots.filter((slot) => slot.artworkId && slot.imageStatus === 'ready')

  return {
    exhibition_date: exhibition.date,
    title: exhibition.title ?? '',
    theme: exhibition.theme ?? '',
    artists: Array.from(new Set(slots.map((slot) => slot.artist).filter(Boolean) as string[])),
    artworks: slots.map((slot) => toArtworkSummary(slot, exhibition.date)),
    viewing_date: options.viewingDate,
    is_carried_over: isCarriedOver,
    carried_over_label: isCarriedOver ? `${formatMonthDay(exhibition.date)}의 전시` : null,
    is_archive_view: options.isArchiveView,
  }
}

export function toExhibitionSummary(exhibition: MockExhibition): RawExhibitionSummary {
  const cover = exhibition.slots.find((slot) => slot.position === 1 && slot.artworkId)
  const viewed = viewedCount(exhibition.date)
  return {
    exhibition_date: exhibition.date,
    title: exhibition.title ?? '',
    cover_image: cover ? imageOf(cover) : null,
    artwork_count: ARTWORK_COUNT,
    viewed_artwork_count: viewed,
    is_viewed: viewed > 0,
  }
}

export function toAdminSlot(slot: MockSlot): RawAdminArtworkSlot {
  return {
    position: slot.position,
    artwork_id: slot.artworkId,
    title: slot.title,
    artist: slot.artist,
    year_text: slot.yearText,
    description: slot.description,
    collection: slot.collection,
    source_url: slot.sourceUrl,
    image_status: slot.imageStatus,
    image: slot.imageStatus === 'ready' ? imageOf(slot) : null,
    image_error_code: slot.imageStatus === 'failed' ? 'UPLOAD_EXPIRED' : null,
    is_complete: slotIsComplete(slot),
    version: slot.version,
  }
}

export function toSessionUser(member: MockMember): RawSessionUser {
  return {
    id: member.id,
    name: member.name,
    phone_masked: maskPhone(member.phone),
    role: member.role,
    font_scale: member.role === 'curator' ? 'normal' : (memberFontScale.get(member.id) ?? 'normal'),
    notify_enabled: member.notify_enabled,
    notify_at: member.notify_at,
    must_change_password: mustChangePassword.has(member.id),
    created_at: member.created_at,
  }
}

export function toMemberItem(member: MockMember): RawMemberItem {
  const { password: _password, ...rest } = member
  return rest
}

/** 회원별 화면 설정 — 실제로는 `app_user` 컬럼이다. 데모에서는 별도 맵으로 둔다. */
export const memberFontScale = new Map<string, 'normal' | 'large'>()
export const mustChangePassword = new Set<string>()

/** 로그인한 회원이 없으면 목 핸들러가 401을 흉내 낸다. */
export function requireMember(): MockMember {
  const member = db.members.find((candidate) => candidate.id === db.currentUserId)
  if (!member) {
    mockFail(ERROR_CODES.authRequired, 401)
  }
  return member
}

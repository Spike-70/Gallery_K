import { ERROR_CODES } from '@/shared/api/ApiError'
import type { PaginationMeta } from '@/shared/api/envelope'
import { paginateWithPage } from '@/shared/api/pagination'
import type {
  RawAdminExhibitionDay,
  RawAdminExhibitionDetail,
  RawAdminSummary,
  RawAppSetting,
  RawExhibitionDetail,
  RawMemberItem,
  RawMemberStatsDay,
  RawNoticeItem,
  RawStatsDay,
} from '@/shared/api/types'
import { ARTWORK_COUNT, CALENDAR_DEFAULT_DAYS, MEMBER_PAGE_SIZE } from '@/shared/config/constants'
import { dateSeries } from '@/shared/lib/date'
import { normalizePhone } from '@/shared/lib/phone'
import type { IsoDate, Uuid } from '@/shared/types/utility'

import {
  type MockExhibition,
  canPublish,
  db,
  dayStatus,
  editModeFor,
  ensureExhibition,
  exhibitionOn,
  findArtwork,
  hasDraftWork,
  nowIso,
  publishBlockers,
  publishedExhibitions,
  reevaluatePublish,
  shiftDate,
  slotIsComplete,
  touchDraft,
  uuid,
} from '@/mocks/db'
import { mockDelay, mockFail, seededRandom } from '@/mocks/lib/mockClient'
import {
  mustChangePassword,
  requireMember,
  toAdminSlot,
  toExhibitionDetail,
  toMemberItem,
} from '@/mocks/lib/serializers'

/**
 * 관리자 핸들러 — API 명세서 §9
 * 큐레이터 권한 판정은 **서버 몫**이다. 목도 같은 위치에서 판정한다(PRD §8.4).
 */
function requireCurator() {
  const member = requireMember()
  if (member.role !== 'curator') {
    mockFail(ERROR_CODES.authForbidden, 403)
  }
  return member
}

// ── §9.1 요약 ───────────────────────────────────────────────────────────
export function getAdminSummary(): Promise<RawAdminSummary> {
  requireCurator()
  const random = seededRandom(db.members.length * 31)
  const totalMembers = db.members.filter((member) => !member.is_blocked && member.role === 'viewer').length
  const weeklyActive = Math.round(totalMembers * 0.68)
  const current = exhibitionOn(db.today)
  const carriedDays = current && current.date < db.today
    ? Math.round((new Date(db.today).getTime() - new Date(current.date).getTime()) / 86400000)
    : 0

  return mockDelay(
    {
      today_entrant_count: 12 + Math.floor(random() * 6),
      weekly_active_ratio: totalMembers === 0 ? 0 : Number((weeklyActive / totalMembers).toFixed(3)),
      weekly_active_count: weeklyActive,
      total_member_count: totalMembers,
      carried_over_days: carriedDays,
      pending_draft_count: Array.from(db.exhibitions.values()).filter(
        (exhibition) => !exhibition.isPublished && hasDraftWork(exhibition),
      ).length,
      lead_time_days: countLeadTime(),
    },
    260,
  )
}

/** 오늘부터 연속으로 발행 준비된 날 수 */
function countLeadTime(): number {
  let days = 0
  for (let offset = 0; offset < 30; offset += 1) {
    const date = shiftDate(new Date(db.today), offset)
    const exhibition = db.exhibitions.get(date)
    if (exhibition && (exhibition.isPublished || canPublish(exhibition))) days += 1
    else break
  }
  return days
}

// ── §9.2 달력 ───────────────────────────────────────────────────────────
function toCalendarDay(date: IsoDate): RawAdminExhibitionDay {
  const own = db.exhibitions.get(date)
  const { status, carriedFrom } = dayStatus(date)
  const completeCount = own ? own.slots.filter(slotIsComplete).length : 0

  return {
    date,
    status,
    title: own?.title ?? null,
    carried_from_date: carriedFrom?.date ?? null,
    carried_from_title: carriedFrom?.title ?? null,
    has_draft: Boolean(own && !own.isPublished && hasDraftWork(own)),
    draft_progress: {
      artwork_count: own ? own.slots.filter((slot) => slot.artworkId).length : 0,
      complete_artwork_count: completeCount,
      has_title: Boolean(own?.title),
      has_theme: Boolean(own?.theme),
    },
    is_hidden: Boolean(own?.isHidden),
    is_editable: editModeFor(date) !== 'locked',
    edit_mode: editModeFor(date),
    is_today: date === db.today,
    updated_at: own?.draftUpdatedAt ?? null,
  }
}

/**
 * `GET /admin/exhibitions/calendar`
 * `days`는 요청 범위의 **모든 날짜를 빠짐없이** 포함한다. 클라이언트가 날짜 시리즈를 만들지 않는다.
 */
export function getCalendar(params: {
  direction?: 'future' | 'past'
  cursor?: string | null
  limit?: number
}): Promise<{ data: { days: RawAdminExhibitionDay[] }; pagination: PaginationMeta }> {
  requireCurator()
  const limit = params.limit ?? CALENDAR_DEFAULT_DAYS
  const offset = params.cursor ? Number(atob(params.cursor)) : 0

  const dates =
    params.direction === 'past'
      ? dateSeries(shiftDate(new Date(db.today), -(offset + limit)), limit)
      : dateSeries(shiftDate(new Date(db.today), offset), limit)

  const nextOffset = offset + limit
  return mockDelay(
    {
      data: { days: dates.map(toCalendarDay) },
      pagination: {
        mode: 'cursor',
        limit,
        count: dates.length,
        has_more: nextOffset < 90,
        next_cursor: nextOffset < 90 ? btoa(String(nextOffset)) : null,
        page: null,
        total_count: null,
        total_pages: null,
      },
    },
    240,
  )
}

// ── §9.3~§9.7 전시 편집 ────────────────────────────────────────────────
function toAdminDetail(exhibition: MockExhibition): RawAdminExhibitionDetail {
  const carrySource =
    editModeFor(exhibition.date) === 'carry_draft'
      ? {
          from_date: exhibition.date,
          artwork_count: exhibition.slots.filter((slot) => slot.artworkId).length,
        }
      : null

  return {
    exhibition_date: exhibition.date,
    title: exhibition.title,
    theme: exhibition.theme,
    is_published: exhibition.isPublished,
    published_at: exhibition.publishedAt,
    is_hidden: exhibition.isHidden,
    edit_mode: editModeFor(exhibition.date),
    can_publish: canPublish(exhibition),
    publish_blockers: publishBlockers(exhibition),
    slots: exhibition.slots.map(toAdminSlot),
    version: exhibition.version,
    draft_updated_at: exhibition.draftUpdatedAt,
    carry_draft_source: carrySource,
  }
}

/** `GET /admin/exhibitions/{date}` — 행이 없어도 빈 12슬롯을 반환한다 */
export function getAdminExhibition(date: IsoDate): Promise<RawAdminExhibitionDetail> {
  requireCurator()
  return mockDelay(toAdminDetail(ensureExhibition(date)), 240)
}

/** `PUT /admin/exhibitions/{date}` — 제목·테마 저장(자동 임시저장의 대상) */
export async function saveExhibitionMeta(
  date: IsoDate,
  input: { title: string | null; theme: string | null; version?: number },
): Promise<{
  exhibition_date: IsoDate
  version: number
  draft_updated_at: string | null
  is_published: boolean
  published_at: string | null
  can_publish: boolean
  publish_blockers: string[]
  published_now: boolean
}> {
  requireCurator()
  if (date < db.today && !db.exhibitions.get(date)?.isPublished && !hasDraftWork(db.exhibitions.get(date))) {
    mockFail(ERROR_CODES.exhibitionBackfillForbidden, 409, { details: { date, today: db.today } })
  }

  const exhibition = ensureExhibition(date)
  exhibition.title = input.title
  exhibition.theme = input.theme
  touchDraft(exhibition)
  const { publishedNow } = reevaluatePublish(exhibition)

  return mockDelay(
    {
      exhibition_date: exhibition.date,
      version: exhibition.version,
      draft_updated_at: exhibition.draftUpdatedAt,
      is_published: exhibition.isPublished,
      published_at: exhibition.publishedAt,
      can_publish: canPublish(exhibition),
      publish_blockers: publishBlockers(exhibition),
      published_now: publishedNow,
    },
    380,
  )
}

type SlotSaveResult = {
  slot: ReturnType<typeof toAdminSlot>
  exhibition: {
    version: number
    can_publish: boolean
    publish_blockers: string[]
    is_published: boolean
    published_now: boolean
  }
}

/** `PUT /admin/exhibitions/{date}/artworks/{position}` — 전시 상태를 함께 반환한다 */
export async function saveArtworkSlot(
  date: IsoDate,
  position: number,
  input: {
    title: string | null
    artist: string | null
    yearText: string | null
    description: string | null
    collection: string | null
    sourceUrl: string | null
  },
): Promise<SlotSaveResult> {
  requireCurator()
  const exhibition = ensureExhibition(date)
  const slot = exhibition.slots.find((candidate) => candidate.position === position)
  if (!slot) mockFail(ERROR_CODES.notFound, 404)

  slot.title = input.title
  slot.artist = input.artist
  slot.yearText = input.yearText
  slot.description = input.description
  slot.collection = input.collection
  slot.sourceUrl = input.sourceUrl
  slot.version += 1
  touchDraft(exhibition)
  const { publishedNow } = reevaluatePublish(exhibition)

  return mockDelay(
    {
      slot: toAdminSlot(slot),
      exhibition: {
        version: exhibition.version,
        can_publish: canPublish(exhibition),
        publish_blockers: publishBlockers(exhibition),
        is_published: exhibition.isPublished,
        published_now: publishedNow,
      },
    },
    360,
  )
}

/** `DELETE /admin/exhibitions/{date}/artworks/{position}` — 슬롯 비우기 */
export async function clearArtworkSlot(date: IsoDate, position: number): Promise<SlotSaveResult> {
  requireCurator()
  const exhibition = ensureExhibition(date)
  const slot = exhibition.slots.find((candidate) => candidate.position === position)
  if (!slot) mockFail(ERROR_CODES.notFound, 404)

  slot.artworkId = null
  slot.title = null
  slot.artist = null
  slot.yearText = null
  slot.description = null
  slot.collection = null
  slot.sourceUrl = null
  slot.imageStatus = 'empty'
  slot.imageSeed = null
  slot.imageObjectUrl = null
  touchDraft(exhibition)

  return mockDelay(
    {
      slot: toAdminSlot(slot),
      exhibition: {
        version: exhibition.version,
        can_publish: canPublish(exhibition),
        publish_blockers: publishBlockers(exhibition),
        is_published: exhibition.isPublished,
        published_now: false,
      },
    },
    280,
  )
}

/** `POST /admin/exhibitions/{date}/artworks/reorder` — 최종 상태 선언이므로 재시도가 안전하다 */
export async function reorderArtworks(
  date: IsoDate,
  order: { artworkId: Uuid; position: number }[],
): Promise<{ slots: ReturnType<typeof toAdminSlot>[] }> {
  requireCurator()
  const exhibition = ensureExhibition(date)
  const byArtwork = new Map(exhibition.slots.filter((slot) => slot.artworkId).map((slot) => [slot.artworkId, slot]))

  const next = exhibition.slots.map((slot) => ({ ...slot, artworkId: null as Uuid | null }))
  for (const entry of order) {
    const source = byArtwork.get(entry.artworkId)
    if (!source) continue
    next[entry.position - 1] = { ...source, position: entry.position }
  }
  exhibition.slots = next.map((slot, index) =>
    slot.artworkId ? slot : { ...slot, position: index + 1, artworkId: null, imageStatus: 'empty', imageSeed: null, imageObjectUrl: null },
  )
  touchDraft(exhibition)

  return mockDelay({ slots: exhibition.slots.map(toAdminSlot) }, 300)
}

/** `POST /admin/exhibitions/{date}/artworks/upload-urls` — Presigned URL 배치 발급 */
export async function requestUploadUrls(
  date: IsoDate,
  files: { position: number; filename: string; contentType: string; sizeBytes: number; objectUrl?: string }[],
): Promise<{
  uploads: {
    position: number
    artwork_id: Uuid
    upload_url: string
    method: 'PUT'
    headers: Record<string, string>
    object_key: string
    expires_at: string
  }[]
}> {
  requireCurator()
  const exhibition = ensureExhibition(date)

  const uploads = files.map((file) => {
    const slot = exhibition.slots.find((candidate) => candidate.position === file.position)
    if (!slot) mockFail(ERROR_CODES.notFound, 404)
    const artworkId = slot.artworkId ?? uuid(`up${date}${file.position}`, file.position)
    slot.artworkId = artworkId
    slot.imageStatus = 'uploading'
    // 데모에서는 실제 파일을 objectURL로 그대로 보여준다.
    slot.imageObjectUrl = file.objectUrl ?? null
    return {
      position: file.position,
      artwork_id: artworkId,
      upload_url: `mock://upload/${date}/${file.position}`,
      method: 'PUT' as const,
      headers: { 'Content-Type': file.contentType },
      object_key: `artworks/${date}/${file.position}`,
      expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
    }
  })

  touchDraft(exhibition)
  return mockDelay({ uploads }, 320)
}

/**
 * `POST /admin/artworks/{id}/image/complete`
 * 처리 파이프라인을 흉내 낸다: `processing` → 2.4초 뒤 `ready`.
 * 화면의 폴링 규약(2초 간격)이 데모에서도 그대로 관찰된다.
 */
export async function completeImageUpload(artworkId: Uuid): Promise<{
  artwork_id: Uuid
  image_status: 'processing' | 'ready'
  estimated_ready_in_seconds: number
}> {
  requireCurator()
  const found = findArtwork(artworkId)
  if (!found) mockFail(ERROR_CODES.artworkNotFound, 404)

  const { slot, exhibition } = found
  if (slot.imageStatus === 'ready') {
    return mockDelay({ artwork_id: artworkId, image_status: 'ready', estimated_ready_in_seconds: 0 }, 120)
  }

  slot.imageStatus = 'processing'
  window.setTimeout(() => {
    slot.imageStatus = 'ready'
    if (slot.imageSeed === null && !slot.imageObjectUrl) {
      slot.imageSeed = Math.floor(Math.random() * 120)
    }
    reevaluatePublish(exhibition)
  }, 2400)

  return mockDelay({ artwork_id: artworkId, image_status: 'processing', estimated_ready_in_seconds: 3 }, 160)
}

/** `POST /admin/exhibitions/{date}/hide` · `/unhide` */
export async function setExhibitionHidden(
  date: IsoDate,
  hidden: boolean,
): Promise<{ exhibition_date: IsoDate; is_hidden: boolean; hidden_at: string | null; current_exhibition_date: string }> {
  requireCurator()
  const exhibition = db.exhibitions.get(date)
  if (!exhibition || !exhibition.isPublished) {
    mockFail(ERROR_CODES.exhibitionNotFound, 404)
  }
  exhibition.isHidden = hidden
  const current = publishedExhibitions().find((item) => item.date <= db.today)

  return mockDelay(
    {
      exhibition_date: date,
      is_hidden: hidden,
      hidden_at: hidden ? nowIso() : null,
      current_exhibition_date: current?.date ?? db.today,
    },
    280,
  )
}

/** `POST /admin/exhibitions/{date}/carry-draft` — 복사가 아니라 **이동**이다 */
export async function carryDraft(date: IsoDate): Promise<{
  from_date: IsoDate
  to_date: IsoDate
  moved_artwork_count: number
  exhibition: RawAdminExhibitionDetail
}> {
  requireCurator()
  const source = db.exhibitions.get(date)
  if (!source || source.isPublished || !hasDraftWork(source)) {
    mockFail(ERROR_CODES.draftNotFound, 404)
  }
  const target = db.exhibitions.get(db.today)
  if (hasDraftWork(target)) {
    mockFail(ERROR_CODES.draftTargetOccupied, 409, { details: { target_date: db.today } })
  }

  const moved = source.slots.filter((slot) => slot.artworkId).length
  const carried: MockExhibition = {
    ...source,
    date: db.today,
    version: 1,
    draftUpdatedAt: nowIso(),
    slots: source.slots.map((slot) => ({ ...slot })),
  }
  db.exhibitions.set(db.today, carried)
  db.exhibitions.delete(date)

  return mockDelay({ from_date: date, to_date: db.today, moved_artwork_count: moved, exhibition: toAdminDetail(carried) }, 480)
}

/** `GET /admin/exhibitions/{date}/preview` — 관람자와 **동일한 스키마**를 준다 */
export function getExhibitionPreview(date: IsoDate): Promise<RawExhibitionDetail> {
  requireCurator()
  const exhibition = ensureExhibition(date)
  return mockDelay(
    toExhibitionDetail(exhibition, { viewingDate: date, isArchiveView: false, includeIncomplete: true }),
    280,
  )
}

// ── §9.13~§9.16 회원 관리 ──────────────────────────────────────────────
export function getMembers(params: {
  query?: string
  status?: 'all' | 'active' | 'blocked'
  notify?: 'all' | 'on' | 'off'
  sort?: string
  page?: number
  limit?: number
}): Promise<{
  data: { members: RawMemberItem[]; signup_open: boolean }
  pagination: PaginationMeta
}> {
  requireCurator()
  let list = db.members.map(toMemberItem)

  if (params.query) {
    const query = params.query.trim()
    const digits = normalizePhone(query)
    list = list.filter(
      (member) => member.name.includes(query) || (digits.length > 0 && member.phone === digits),
    )
  }
  if (params.status === 'active') list = list.filter((member) => !member.is_blocked)
  if (params.status === 'blocked') list = list.filter((member) => member.is_blocked)
  if (params.notify === 'on') list = list.filter((member) => member.notify_enabled)
  if (params.notify === 'off') list = list.filter((member) => !member.notify_enabled)

  const sort = params.sort ?? '-created_at'
  const direction = sort.startsWith('-') ? -1 : 1
  const key = sort.replace('-', '') as 'created_at' | 'name' | 'last_viewed_on'
  list.sort((a, b) => {
    const left = String(a[key] ?? '')
    const right = String(b[key] ?? '')
    return left < right ? -direction : left > right ? direction : 0
  })

  const { page, meta } = paginateWithPage(list, params.limit ?? MEMBER_PAGE_SIZE, params.page ?? 1)
  return mockDelay(
    { data: { members: page.items, signup_open: Boolean(db.settings.find((s) => s.key === 'signup_open')?.value) }, pagination: meta },
    280,
  )
}

/** `POST /admin/members` — 가입 잠금 상태에서도 큐레이터는 계정을 만들 수 있다 */
export async function createMember(input: {
  phone: string
  name: string
  initialPassword: string
}): Promise<{ member: RawMemberItem }> {
  requireCurator()
  const phone = normalizePhone(input.phone)
  if (db.members.some((member) => member.phone === phone)) {
    mockFail(ERROR_CODES.signupPhoneTaken, 409)
  }

  const created = {
    id: uuid(`mbc${db.members.length}`, db.members.length),
    name: input.name,
    phone,
    role: 'viewer' as const,
    created_at: nowIso(),
    created_via: 'curator' as const,
    is_blocked: false,
    blocked_at: null,
    notify_enabled: false,
    notify_at: '07:30',
    push_status: 'none' as const,
    push_platforms: [],
    last_login_at: null,
    last_viewed_on: null,
    password: input.initialPassword,
  }
  db.members.push(created)
  mustChangePassword.add(created.id)

  return mockDelay({ member: toMemberItem(created) }, 420)
}

/** `POST /admin/members/{id}/block` · `/unblock` — 멱등하다 */
export async function setMemberBlocked(id: Uuid, blocked: boolean): Promise<{ member: RawMemberItem }> {
  requireCurator()
  const member = db.members.find((candidate) => candidate.id === id)
  if (!member) mockFail(ERROR_CODES.memberNotFound, 404)
  if (member.role === 'curator') mockFail(ERROR_CODES.memberCuratorImmutable, 403)

  member.is_blocked = blocked
  member.blocked_at = blocked ? nowIso() : null
  return mockDelay({ member: toMemberItem(member) }, 320)
}

/** `POST /admin/members/{id}/reset-password` */
export async function resetMemberPassword(id: Uuid, newPassword: string): Promise<{ member: RawMemberItem }> {
  requireCurator()
  const member = db.members.find((candidate) => candidate.id === id)
  if (!member) mockFail(ERROR_CODES.memberNotFound, 404)

  member.password = newPassword
  mustChangePassword.add(member.id)
  return mockDelay({ member: toMemberItem(member) }, 360)
}

// ── §9.17~§9.18 설정 · 공지 ────────────────────────────────────────────
export function getAdminSettings(): Promise<{ settings: RawAppSetting[] }> {
  requireCurator()
  return mockDelay({ settings: db.settings }, 200)
}

export async function updateAdminSettings(values: Record<string, string | number | boolean>): Promise<{
  settings: RawAppSetting[]
}> {
  requireCurator()
  for (const [key, value] of Object.entries(values)) {
    const setting = db.settings.find((candidate) => candidate.key === key)
    if (!setting) mockFail(ERROR_CODES.notFound, 400, { details: { key } })
    if (!setting.is_mutable) mockFail('SETTING_IMMUTABLE', 403, { details: { key } })
    setting.value = value
    setting.updated_at = nowIso()
  }
  return mockDelay({ settings: db.settings }, 280)
}

export function getNotices(includePast = false): Promise<{ notices: RawNoticeItem[] }> {
  requireCurator()
  const notices = includePast ? db.notices : db.notices.filter((notice) => notice.ends_on >= db.today)
  return mockDelay({ notices }, 220)
}

export async function createNotice(input: {
  startsOn: IsoDate
  endsOn: IsoDate
  body: string
}): Promise<{ notice: RawNoticeItem }> {
  requireCurator()
  if (input.endsOn < input.startsOn) {
    mockFail(ERROR_CODES.noticePeriodInvalid, 422)
  }
  const overlap = db.notices.find(
    (notice) => notice.is_active && notice.starts_on <= input.endsOn && notice.ends_on >= input.startsOn,
  )
  if (overlap) {
    mockFail(ERROR_CODES.noticePeriodOverlap, 409, { details: { conflict_notice_id: overlap.id } })
  }

  const notice: RawNoticeItem = {
    id: uuid(`nt${db.notices.length}`, db.notices.length + 2),
    starts_on: input.startsOn,
    ends_on: input.endsOn,
    body: input.body,
    is_active: true,
  }
  db.notices.push(notice)
  return mockDelay({ notice }, 360)
}

export async function deleteNotice(id: Uuid): Promise<Record<string, never>> {
  requireCurator()
  const notice = db.notices.find((candidate) => candidate.id === id)
  if (notice) notice.is_active = false
  db.notices = db.notices.filter((candidate) => candidate.is_active)
  return mockDelay({}, 240)
}

// ── §9.19 통계 (v1.1) ──────────────────────────────────────────────────
export function getDailyStats(days = 7): Promise<{ days: RawStatsDay[] }> {
  requireCurator()
  const random = seededRandom(days * 97)
  const series = dateSeries(shiftDate(new Date(db.today), -(days - 1)), days)
  return mockDelay(
    {
      days: series.map((date) => {
        const exhibition = exhibitionOn(date)
        return {
          date,
          exhibition_date: exhibition?.date ?? null,
          exhibition_title: exhibition?.title ?? null,
          is_carried_over: Boolean(exhibition && exhibition.date < date),
          entrant_count: 6 + Math.floor(random() * 12),
          artwork_view_count: 40 + Math.floor(random() * 80),
        }
      }),
    },
    280,
  )
}

export function searchMembersForStats(query: string): Promise<{
  members: { id: Uuid; name: string; phone_masked: string; last_viewed_on: IsoDate | null }[]
}> {
  requireCurator()
  const found = db.members
    .filter((member) => member.role === 'viewer' && member.name.includes(query))
    .slice(0, 20)
    .map((member) => ({
      id: member.id,
      name: member.name,
      phone_masked: `${member.phone.slice(0, 3)}-****-${member.phone.slice(-4)}`,
      last_viewed_on: member.last_viewed_on,
    }))
  return mockDelay({ members: found }, 220)
}

export function getMemberStats(memberId: Uuid, days = 30): Promise<{
  member: { id: Uuid; name: string; phone_masked: string }
  days: RawMemberStatsDay[]
}> {
  requireCurator()
  const member = db.members.find((candidate) => candidate.id === memberId)
  if (!member) mockFail(ERROR_CODES.memberNotFound, 404)

  const random = seededRandom(memberId.length * 41)
  const series = dateSeries(shiftDate(new Date(db.today), -(days - 1)), days)
  return mockDelay(
    {
      member: {
        id: member.id,
        name: member.name,
        phone_masked: `${member.phone.slice(0, 3)}-****-${member.phone.slice(-4)}`,
      },
      days: series.map((date) => {
        const exhibition = exhibitionOn(date)
        const entered = random() > 0.35
        return {
          date,
          exhibition_date: exhibition?.date ?? null,
          exhibition_title: exhibition?.title ?? null,
          entered,
          viewed_artwork_count: entered ? Math.floor(random() * ARTWORK_COUNT) + 1 : 0,
          total_artwork_count: ARTWORK_COUNT,
        }
      }),
    },
    320,
  )
}

import { ARTWORK_COUNT } from '@/shared/config/constants'
import type {
  RawAdminArtworkSlot,
  RawAppSetting,
  RawMemberItem,
  RawNoticeItem,
  RawPushSubscription,
} from '@/shared/api/types'
import type { EditMode, ExhibitionDayStatus } from '@/shared/types/enums'
import { toIsoDate } from '@/shared/lib/date'
import type { IsoDate, Uuid } from '@/shared/types/utility'

import { ARTWORK_SEEDS, PAST_EXHIBITION_SEEDS } from '@/mocks/data/artworkSeeds'
import { DEMO_KEYS, PersistentSet, clearDemo, readDemo, writeDemo } from '@/mocks/lib/demoStorage'

/**
 * 인메모리 목 DB — 데모 전용
 *
 * 화면에서 한 조작이 실제로 반영되도록 **가변 상태**를 유지한다(로그인·설정·자동
 * 저장·차단·발행). 발행 조건 판정처럼 **서버가 소유해야 할 도메인 규칙**도 여기서
 * 계산한다 — 규칙이 화면 코드로 새어 들어가면 실제 API로 교체할 때 남는다.
 *
 * 새로고침하면 초기 시드로 돌아간다. 영속이 필요하면 그때가 백엔드를 붙일 때다.
 */

// ── 유틸 ────────────────────────────────────────────────────────────────
function shiftDate(base: Date, days: number): IsoDate {
  const d = new Date(base)
  d.setDate(base.getDate() + days)
  return toIsoDate(d)
}

function uuid(prefix: string, index: number): Uuid {
  return `${prefix}-${String(index).padStart(4, '0')}-0000-4000-8000-000000000000`.slice(0, 36)
}

function nowIso(): string {
  return new Date().toISOString()
}

// ── 타입 ────────────────────────────────────────────────────────────────
export type MockSlot = {
  position: number
  artworkId: Uuid | null
  title: string | null
  artist: string | null
  yearText: string | null
  description: string | null
  collection: string | null
  sourceUrl: string | null
  imageStatus: RawAdminArtworkSlot['image_status']
  imageSeed: number | null
  /** 데모에서 실제로 올린 파일을 그대로 보여주기 위한 objectURL */
  imageObjectUrl: string | null
  ratio: number
  version: number
}

export type MockExhibition = {
  date: IsoDate
  title: string | null
  theme: string | null
  slots: MockSlot[]
  isPublished: boolean
  publishedAt: string | null
  isHidden: boolean
  version: number
  draftUpdatedAt: string | null
}

export type MockMember = RawMemberItem & { password: string }

// ── 시드 조립 ───────────────────────────────────────────────────────────
const TODAY_BASE = new Date()
const TODAY: IsoDate = toIsoDate(TODAY_BASE)

function emptySlot(position: number): MockSlot {
  return {
    position,
    artworkId: null,
    title: null,
    artist: null,
    yearText: null,
    description: null,
    collection: null,
    sourceUrl: null,
    imageStatus: 'empty',
    imageSeed: null,
    imageObjectUrl: null,
    ratio: 4 / 5,
    version: 1,
  }
}

function filledSlot(position: number, exhibitionIndex: number): MockSlot {
  // 전시마다 그림 순서를 회전시켜 아카이브가 서로 다른 얼굴을 갖게 한다.
  const seed = ARTWORK_SEEDS[(position - 1 + exhibitionIndex * 5) % ARTWORK_SEEDS.length]
  return {
    position,
    artworkId: uuid(`aw${exhibitionIndex}${position}`, position),
    title: seed.title,
    artist: seed.artist,
    yearText: seed.yearText,
    description: seed.description,
    collection: seed.collection,
    sourceUrl: seed.sourceUrl,
    imageStatus: 'ready',
    imageSeed: exhibitionIndex * 12 + position,
    imageObjectUrl: null,
    ratio: seed.ratio,
    version: 1,
  }
}

function publishedExhibition(date: IsoDate, index: number): MockExhibition {
  const seed = PAST_EXHIBITION_SEEDS[index % PAST_EXHIBITION_SEEDS.length]
  return {
    date,
    title: seed.title,
    theme: seed.theme,
    slots: Array.from({ length: ARTWORK_COUNT }, (_, i) => filledSlot(i + 1, index)),
    isPublished: true,
    publishedAt: `${date}T22:10:00Z`,
    isHidden: false,
    version: 3,
    draftUpdatedAt: `${date}T22:10:00Z`,
  }
}

/**
 * 발행일 배치.
 * 중간에 비어 있는 날(오늘-3, 오늘-7)을 남겨 **연장(↑) 상태**를 관리자 달력에서
 * 실제로 볼 수 있게 한다(PRD §4.3).
 */
const PUBLISHED_OFFSETS = [0, -1, -2, -4, -5, -6, -8, -9, -10]

function seedExhibitions(): Map<IsoDate, MockExhibition> {
  const map = new Map<IsoDate, MockExhibition>()

  PUBLISHED_OFFSETS.forEach((offset, index) => {
    const date = shiftDate(TODAY_BASE, offset)
    map.set(date, publishedExhibition(date, index))
  })

  // 내일 자 드래프트 — 7/12 진행 중(`N` + 진행률 표시)
  const tomorrow = shiftDate(TODAY_BASE, 1)
  const draftSlots = Array.from({ length: ARTWORK_COUNT }, (_, i) =>
    i < 7 ? filledSlot(i + 1, 3) : emptySlot(i + 1),
  )
  map.set(tomorrow, {
    date: tomorrow,
    title: '창을 여는 사람',
    theme: null,
    slots: draftSlots,
    isPublished: false,
    publishedAt: null,
    isHidden: false,
    version: 2,
    draftUpdatedAt: nowIso(),
  })

  // 과거 미발행 드래프트 — `이어서 쓰기` 대상(PRD 부록 B)
  const staleDate = shiftDate(TODAY_BASE, -3)
  map.set(staleDate, {
    date: staleDate,
    title: '겨울의 초입',
    theme: '차가운 공기에서 색이 어떻게 달라지는지 보려고 모았습니다.',
    slots: Array.from({ length: ARTWORK_COUNT }, (_, i) => (i < 4 ? filledSlot(i + 1, 5) : emptySlot(i + 1))),
    isPublished: false,
    publishedAt: null,
    isHidden: false,
    version: 4,
    draftUpdatedAt: `${staleDate}T13:20:00Z`,
  })

  return map
}

function seedMembers(): MockMember[] {
  const names = [
    '김서연', '박정호', '이미경', '최윤아', '정대현', '한소희',
    '오지훈', '배수민', '문가영', '신동욱', '강예린', '윤재석',
  ]
  return names.map((name, index) => {
    const isCurator = index === 0
    const phone = isCurator ? '01000000001' : `0101234${String(5670 + index).padStart(4, '0')}`
    const pushStatus = index % 5 === 0 ? 'none' : index % 7 === 0 ? 'inactive' : 'active'
    return {
      id: uuid(`mb${index}`, index),
      name: isCurator ? '큐레이터 K' : name,
      phone,
      role: isCurator ? 'curator' : 'viewer',
      created_at: shiftDate(TODAY_BASE, -60 + index * 4) + 'T02:00:00Z',
      created_via: index % 6 === 0 ? 'curator' : 'self',
      is_blocked: index === 9,
      blocked_at: index === 9 ? shiftDate(TODAY_BASE, -5) + 'T05:00:00Z' : null,
      notify_enabled: pushStatus !== 'none',
      notify_at: '07:30',
      push_status: pushStatus,
      push_platforms: index % 3 === 0 ? ['ios'] : index % 3 === 1 ? ['android'] : ['desktop'],
      last_login_at: shiftDate(TODAY_BASE, -(index % 4)) + 'T21:40:00Z',
      last_viewed_on: index % 5 === 4 ? null : shiftDate(TODAY_BASE, -(index % 3)),
      password: isCurator ? 'curator1234' : 'gallery1234',
    }
  })
}

function seedNotices(): RawNoticeItem[] {
  return [
    {
      id: uuid('nt1', 1),
      starts_on: shiftDate(TODAY_BASE, 12),
      ends_on: shiftDate(TODAY_BASE, 16),
      body: '9월 5일까지 잠시 쉬어갑니다. 그동안 지난 전시를 둘러보세요.',
      is_active: true,
    },
  ]
}

function seedSettings(): RawAppSetting[] {
  return [
    { key: 'signup_open', value: true, value_type: 'boolean', description: '새로운 회원의 가입을 받습니다.', is_mutable: true, updated_at: null },
    { key: 'notify_default_hour', value: '07:30', value_type: 'string', description: '가입 직후 적용되는 기본 알림 시각입니다.', is_mutable: true, updated_at: null },
    { key: 'notify_cutoff_hour', value: 21, value_type: 'number', description: '이 시각을 넘기면 그날의 알림을 보내지 않습니다.', is_mutable: true, updated_at: null },
    { key: 'archive_size', value: 30, value_type: 'number', description: '지난 전시 목록에 보여줄 전시 개수입니다.', is_mutable: true, updated_at: null },
    { key: 'media_signing_mode', value: 'cookie', value_type: 'string', description: '이미지 접근 방식입니다. 변경할 수 없습니다.', is_mutable: false, updated_at: null },
  ]
}

// ── 상태 ────────────────────────────────────────────────────────────────
type MockDb = {
  today: IsoDate
  exhibitions: Map<IsoDate, MockExhibition>
  members: MockMember[]
  notices: RawNoticeItem[]
  settings: RawAppSetting[]
  pushSubscriptions: RawPushSubscription[]
  /** 로그인한 회원 id. `null`이면 비로그인 */
  currentUserId: Uuid | null
  /** `${exhibitionDate}:${artworkId}` 집합 — 열람 표식의 원천(PRD §6.5) */
  viewedArtworks: Set<string>
  /** 입장한 관람일 집합 */
  enteredDates: Set<IsoDate>
  mediaSessionExpiresAt: string | null
}

/**
 * 세션만 브라우저에 남긴다 — 새로고침해도 로그인이 유지되어야 90일 자동 로그인(GAP-14)을
 * 데모에서 보여줄 수 있다. 전시 원고·업로드는 일부러 남기지 않는다(`demoStorage.ts` 참조).
 */
type DemoSession = { currentUserId: Uuid | null; mediaSessionExpiresAt: string | null }

const restoredSession = readDemo<DemoSession>(DEMO_KEYS.session, {
  currentUserId: null,
  mediaSessionExpiresAt: null,
})

let sessionState: DemoSession = { ...restoredSession }

function persistSession(): void {
  writeDemo(DEMO_KEYS.session, sessionState)
}

export const db: MockDb = {
  today: TODAY,
  exhibitions: seedExhibitions(),
  members: seedMembers(),
  notices: seedNotices(),
  settings: seedSettings(),
  pushSubscriptions: [],

  /**
   * 핸들러는 평소처럼 `db.currentUserId = ...` 로 쓴다.
   * 접근자가 보존을 대신 처리하므로 **핸들러에는 데모 전용 코드가 한 줄도 들어가지 않는다.**
   */
  get currentUserId() {
    return sessionState.currentUserId
  },
  set currentUserId(value: Uuid | null) {
    sessionState.currentUserId = value
    persistSession()
  },
  get mediaSessionExpiresAt() {
    return sessionState.mediaSessionExpiresAt
  },
  set mediaSessionExpiresAt(value: string | null) {
    sessionState.mediaSessionExpiresAt = value
    persistSession()
  },

  viewedArtworks: new PersistentSet<string>(DEMO_KEYS.viewedArtworks),
  enteredDates: new PersistentSet<IsoDate>(DEMO_KEYS.enteredDates),
}

/** 데모 로그인 계정 — 로그인 화면의 안내 카드가 참조한다. */
export const DEMO_ACCOUNTS = {
  viewer: { phone: '010-1234-5671', password: 'gallery1234', label: '관람자' },
  curator: { phone: '010-0000-0001', password: 'curator1234', label: '큐레이터' },
} as const

// ── 파생 계산 (서버가 소유해야 할 규칙) ────────────────────────────────
export function getSetting<T>(key: string, fallback: T): T {
  const found = db.settings.find((setting) => setting.key === key)
  return (found?.value as T) ?? fallback
}

export function slotIsComplete(slot: MockSlot): boolean {
  return Boolean(slot.imageStatus === 'ready' && slot.title && slot.artist && slot.description)
}

/** 발행 조건 — PRD §6.10. 조건이 채워지면 자동으로 걸린다. 발행 버튼은 없다. */
export function publishBlockers(exhibition: MockExhibition): string[] {
  const blockers: string[] = []
  if (!exhibition.title) blockers.push('missing_title')
  if (!exhibition.theme) blockers.push('missing_theme')
  for (const slot of exhibition.slots) {
    if (!slotIsComplete(slot)) blockers.push(`incomplete_artwork:${slot.position}`)
  }
  return blockers
}

export function canPublish(exhibition: MockExhibition): boolean {
  return publishBlockers(exhibition).length === 0
}

/** 저장 시마다 발행 조건을 재평가한다. 처음 충족된 순간을 알려 준다. */
export function reevaluatePublish(exhibition: MockExhibition): { publishedNow: boolean } {
  const eligible = canPublish(exhibition)
  if (eligible && !exhibition.isPublished) {
    exhibition.isPublished = true
    exhibition.publishedAt = nowIso()
    return { publishedNow: true }
  }
  return { publishedNow: false }
}

export function touchDraft(exhibition: MockExhibition): void {
  exhibition.version += 1
  exhibition.draftUpdatedAt = nowIso()
}

/** 발행되어 공개 중인 전시만 최신순으로 */
export function publishedExhibitions(): MockExhibition[] {
  return Array.from(db.exhibitions.values())
    .filter((exhibition) => exhibition.isPublished && !exhibition.isHidden)
    .sort((a, b) => (a.date < b.date ? 1 : -1))
}

/**
 * 지금 걸려 있는 전시 — PRD §4.3 규칙 1.
 * 오늘 발행분이 없으면 직전 발행 전시를 그대로 건다(연장). 오류가 아니다.
 */
export function currentExhibition(): MockExhibition | null {
  const candidates = publishedExhibitions().filter((exhibition) => exhibition.date <= db.today)
  return candidates[0] ?? null
}

/** 특정 날짜 기준으로 걸려 있던 전시 */
export function exhibitionOn(date: IsoDate): MockExhibition | null {
  const candidates = publishedExhibitions().filter((exhibition) => exhibition.date <= date)
  return candidates[0] ?? null
}

export function dayStatus(date: IsoDate): { status: ExhibitionDayStatus; carriedFrom: MockExhibition | null } {
  const own = db.exhibitions.get(date)
  if (own?.isPublished && !own.isHidden) return { status: 'published', carriedFrom: null }
  if (date > db.today) return { status: 'empty', carriedFrom: null }
  const carried = exhibitionOn(date)
  if (carried) return { status: 'carried_over', carriedFrom: carried }
  return { status: 'empty', carriedFrom: null }
}

/** `edit_mode`는 **서버가 결정한다**(API 문서 §3.9). 프런트가 날짜를 비교해 재구현하지 않는다. */
export function editModeFor(date: IsoDate): EditMode {
  const exhibition = db.exhibitions.get(date)
  if (date >= db.today) return exhibition ? 'edit' : 'create'
  if (exhibition?.isPublished) return 'edit'
  if (exhibition && exhibition.slots.some((slot) => slot.artworkId) ) return 'carry_draft'
  if (exhibition && (exhibition.title || exhibition.theme)) return 'carry_draft'
  return 'locked'
}

export function ensureExhibition(date: IsoDate): MockExhibition {
  const existing = db.exhibitions.get(date)
  if (existing) return existing
  const created: MockExhibition = {
    date,
    title: null,
    theme: null,
    slots: Array.from({ length: ARTWORK_COUNT }, (_, i) => emptySlot(i + 1)),
    isPublished: false,
    publishedAt: null,
    isHidden: false,
    version: 1,
    draftUpdatedAt: null,
  }
  db.exhibitions.set(date, created)
  return created
}

export function hasDraftWork(exhibition: MockExhibition | undefined): boolean {
  if (!exhibition) return false
  return Boolean(exhibition.title || exhibition.theme || exhibition.slots.some((slot) => slot.artworkId))
}

export function findArtwork(artworkId: Uuid): { exhibition: MockExhibition; slot: MockSlot } | null {
  for (const exhibition of db.exhibitions.values()) {
    const slot = exhibition.slots.find((candidate) => candidate.artworkId === artworkId)
    if (slot) return { exhibition, slot }
  }
  return null
}

export function currentMember(): MockMember | null {
  if (!db.currentUserId) return null
  return db.members.find((member) => member.id === db.currentUserId) ?? null
}

export function viewedCount(date: IsoDate): number {
  let count = 0
  for (const key of db.viewedArtworks) {
    if (key.startsWith(`${date}:`)) count += 1
  }
  return count
}

export function isViewed(date: IsoDate, artworkId: Uuid | null): boolean {
  return artworkId ? db.viewedArtworks.has(`${date}:${artworkId}`) : false
}

/** 데모 상태를 시드로 되돌린다. 개발 중 화면 재현에 쓴다. */
export function resetDb(): void {
  db.exhibitions = seedExhibitions()
  db.members = seedMembers()
  db.notices = seedNotices()
  db.settings = seedSettings()
  db.pushSubscriptions = []
  sessionState = { currentUserId: null, mediaSessionExpiresAt: null }
  db.viewedArtworks = new PersistentSet<string>(DEMO_KEYS.viewedArtworks)
  db.enteredDates = new PersistentSet<IsoDate>(DEMO_KEYS.enteredDates)
  clearDemo()
}

export { emptySlot, filledSlot, nowIso, shiftDate, TODAY_BASE, uuid }

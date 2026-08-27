import { ERROR_CODES } from '@/shared/api/ApiError'
import type { PaginationMeta } from '@/shared/api/envelope'
import { paginateWithCursor } from '@/shared/api/pagination'
import type { RawExhibitionDetail, RawExhibitionSummary } from '@/shared/api/types'
import { ARCHIVE_LIMIT } from '@/shared/config/constants'
import type { IsoDate } from '@/shared/types/utility'

import { currentExhibition, db, publishedExhibitions } from '@/mocks/db'
import { mockDelay, mockFail } from '@/mocks/lib/mockClient'
import { requireMember, toExhibitionDetail, toExhibitionSummary } from '@/mocks/lib/serializers'

/** `GET /exhibitions/current` — API 명세서 §7.1 */
export async function getCurrentExhibition(): Promise<RawExhibitionDetail> {
  requireMember()
  const exhibition = currentExhibition()
  if (!exhibition) {
    mockFail(ERROR_CODES.exhibitionNotOpened, 404)
  }
  return mockDelay(toExhibitionDetail(exhibition, { viewingDate: db.today, isArchiveView: false }), 380)
}

/** `GET /exhibitions/{date}` — 미발행·숨김·미래 날짜를 모두 동일하게 처리한다 */
export async function getExhibitionByDate(date: IsoDate): Promise<RawExhibitionDetail> {
  requireMember()
  const exhibition = db.exhibitions.get(date)
  if (!exhibition || !exhibition.isPublished || exhibition.isHidden) {
    mockFail(ERROR_CODES.exhibitionNotFound, 404, { details: { date } })
  }
  return mockDelay(toExhibitionDetail(exhibition, { viewingDate: db.today, isArchiveView: true }), 320)
}

/** `GET /exhibitions` — 아카이브 목록(cursor 페이지네이션) */
export async function getArchive(params: { limit?: number; cursor?: string | null }): Promise<{
  data: { exhibitions: RawExhibitionSummary[] }
  pagination: PaginationMeta
}> {
  requireMember()
  const limit = Math.min(params.limit ?? ARCHIVE_LIMIT, ARCHIVE_LIMIT)
  const all = publishedExhibitions()
    .filter((exhibition) => exhibition.date <= db.today)
    .slice(0, ARCHIVE_LIMIT)
    .map(toExhibitionSummary)

  const { page, meta } = paginateWithCursor(all, limit, params.cursor)
  return mockDelay({ data: { exhibitions: page.items }, pagination: meta }, 340)
}

/**
 * `POST /exhibitions/{date}/view` — 입장 기록
 * 관람일은 **서버가 결정**한다. 하루 여러 번 호출해도 지표에 영향이 없다.
 */
export async function logExhibitionView(date: IsoDate): Promise<{
  viewed_on: IsoDate
  is_first_entry_today: boolean
}> {
  requireMember()
  const isFirst = !db.enteredDates.has(db.today)
  db.enteredDates.add(db.today)
  void date
  return mockDelay({ viewed_on: db.today, is_first_entry_today: isFirst }, 120)
}

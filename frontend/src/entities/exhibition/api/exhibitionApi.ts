import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import { type CursorPage, toCursorPage } from '@/shared/api/pagination'
import type { RawExhibitionDetail, RawExhibitionSummary } from '@/shared/api/types'
import { ARCHIVE_LIMIT } from '@/shared/config/constants'
import type { IsoDate } from '@/shared/types/utility'

import { toExhibition, toExhibitionSummary } from '@/entities/exhibition/api/mappers'
import type { Exhibition, ExhibitionSummary } from '@/entities/exhibition/model/types'

/** `GET /exhibitions/current` — 오늘 발행분이 없으면 직전 전시가 온다. 오류가 아니다. */
export async function fetchCurrentExhibition(): Promise<Exhibition> {
  const raw = await httpClient.get<RawExhibitionDetail>(endpoints.exhibitions.current())
  return toExhibition(raw)
}

/** `GET /exhibitions/{date}` — 아카이브에서 연 특정 발행일의 전시 */
export async function fetchExhibitionByDate(date: IsoDate): Promise<Exhibition> {
  const raw = await httpClient.get<RawExhibitionDetail>(endpoints.exhibitions.byDate(date))
  return toExhibition(raw)
}

/** `GET /exhibitions` — 아카이브 목록(cursor 페이지네이션) */
export async function fetchArchive(params: {
  limit?: number
  cursor?: string | null
}): Promise<CursorPage<ExhibitionSummary>> {
  const limit = params.limit ?? ARCHIVE_LIMIT

  const { data, meta } = await httpClient.requestWithMeta<{ exhibitions: RawExhibitionSummary[] }>(
    endpoints.exhibitions.archive(),
    { query: { limit, cursor: params.cursor ?? undefined } },
  )
  return toCursorPage(data.exhibitions.map(toExhibitionSummary), meta.pagination)
}

/**
 * `POST /exhibitions/{date}/view` — 입장 기록
 * 실패해도 조용히 포기한다(프런트 §9.3).
 */
export async function logExhibitionView(date: IsoDate): Promise<void> {
  try {
    await httpClient.post(endpoints.exhibitions.view(date))
  } catch {
    // 사용자에게 오류를 보여주지 않는다(FA-7).
  }
}

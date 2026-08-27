import type { CursorPage } from '@/shared/api/pagination'
// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import { toCursorPage } from '@/shared/api/pagination'
// import type {
//   RawAdminExhibitionDay,
//   RawAdminExhibitionDetail,
//   RawAdminSummary,
//   RawExhibitionDetail,
// } from '@/shared/api/types'
import { CALENDAR_DEFAULT_DAYS } from '@/shared/config/constants'
import type { IsoDate, Uuid } from '@/shared/types/utility'

import { toExhibition } from '@/entities/exhibition/api/mappers'
import {
  toAdminDay,
  toAdminExhibition,
  toAdminSlot,
  toAdminSummary,
} from '@/entities/exhibition/api/adminMappers'
import type {
  AdminExhibition,
  AdminExhibitionDay,
  AdminSlot,
  AdminSummary,
} from '@/entities/exhibition/model/admin'
import type { Exhibition } from '@/entities/exhibition/model/types'

// [MOCK]
import * as adminMock from '@/mocks/handlers/adminHandlers'

/** `GET /admin/summary` — B 홈 요약(API 문서 §9.1) */
export async function fetchAdminSummary(): Promise<AdminSummary> {
  // [API]
  // const raw = await httpClient.get<RawAdminSummary>(endpoints.admin.summary())
  // return toAdminSummary(raw)

  // [MOCK]
  const raw = await adminMock.getAdminSummary()
  return toAdminSummary(raw)
}

/** `GET /admin/exhibitions/calendar` — 범위의 모든 날짜가 빠짐없이 온다 */
export async function fetchCalendar(params: {
  direction?: 'future' | 'past'
  cursor?: string | null
  limit?: number
}): Promise<CursorPage<AdminExhibitionDay>> {
  const limit = params.limit ?? CALENDAR_DEFAULT_DAYS

  // [API]
  // const { data, meta } = await httpClient.requestWithMeta<{ days: RawAdminExhibitionDay[] }>(
  //   endpoints.admin.calendar(),
  //   { query: { direction: params.direction, cursor: params.cursor ?? undefined, limit } },
  // )
  // return toCursorPage(data.days.map(toAdminDay), meta.pagination)

  // [MOCK]
  const result = await adminMock.getCalendar({ ...params, limit })
  return {
    items: result.data.days.map(toAdminDay),
    nextCursor: result.pagination.next_cursor,
    hasMore: result.pagination.has_more,
  }
}

/** `GET /admin/exhibitions/{date}` — 행이 없어도 빈 12슬롯이 온다 */
export async function fetchAdminExhibition(date: IsoDate): Promise<AdminExhibition> {
  // [API]
  // const raw = await httpClient.get<RawAdminExhibitionDetail>(endpoints.admin.exhibition(date))
  // return toAdminExhibition(raw)

  // [MOCK]
  const raw = await adminMock.getAdminExhibition(date)
  return toAdminExhibition(raw)
}

export type SaveMetaResult = {
  version: number
  draftUpdatedAt: string | null
  isPublished: boolean
  canPublish: boolean
  publishBlockers: string[]
  /** 이 요청으로 발행 조건이 **처음** 충족되었는가 */
  publishedNow: boolean
}

/** `PUT /admin/exhibitions/{date}` — 제목·테마를 항상 함께 보낸다(PUT 의미론) */
export async function saveExhibitionMeta(
  date: IsoDate,
  input: { title: string | null; theme: string | null; version?: number },
): Promise<SaveMetaResult> {
  // [API]
  // const raw = await httpClient.put<{
  //   version: number
  //   draft_updated_at: string | null
  //   is_published: boolean
  //   can_publish: boolean
  //   publish_blockers: string[]
  //   published_now: boolean
  // }>(endpoints.admin.exhibition(date), {
  //   title: input.title,
  //   theme: input.theme,
  //   version: input.version,
  // })
  // return {
  //   version: raw.version,
  //   draftUpdatedAt: raw.draft_updated_at,
  //   isPublished: raw.is_published,
  //   canPublish: raw.can_publish,
  //   publishBlockers: raw.publish_blockers,
  //   publishedNow: raw.published_now,
  // }

  // [MOCK]
  const raw = await adminMock.saveExhibitionMeta(date, input)
  return {
    version: raw.version,
    draftUpdatedAt: raw.draft_updated_at,
    isPublished: raw.is_published,
    canPublish: raw.can_publish,
    publishBlockers: raw.publish_blockers,
    publishedNow: raw.published_now,
  }
}

export type SaveSlotResult = {
  slot: AdminSlot
  exhibition: {
    version: number
    canPublish: boolean
    publishBlockers: string[]
    isPublished: boolean
    publishedNow: boolean
  }
}

/** `PUT /admin/exhibitions/{date}/artworks/{position}` — 전시 상태를 함께 받는다 */
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
    version?: number
  },
): Promise<SaveSlotResult> {
  // [API]
  // const raw = await httpClient.put<{ slot: RawAdminArtworkSlot; exhibition: {...} }>(
  //   endpoints.admin.artworkSlot(date, position),
  //   {
  //     title: input.title,
  //     artist: input.artist,
  //     year_text: input.yearText,
  //     description: input.description,
  //     collection: input.collection,
  //     source_url: input.sourceUrl,
  //     version: input.version,
  //   },
  // )
  // return { slot: toAdminSlot(raw.slot), exhibition: { ...camelCase 변환 } }

  // [MOCK]
  const raw = await adminMock.saveArtworkSlot(date, position, input)
  return {
    slot: toAdminSlot(raw.slot),
    exhibition: {
      version: raw.exhibition.version,
      canPublish: raw.exhibition.can_publish,
      publishBlockers: raw.exhibition.publish_blockers,
      isPublished: raw.exhibition.is_published,
      publishedNow: raw.exhibition.published_now,
    },
  }
}

/** `DELETE /admin/exhibitions/{date}/artworks/{position}` */
export async function clearArtworkSlot(date: IsoDate, position: number): Promise<SaveSlotResult> {
  // [API]
  // const raw = await httpClient.delete<...>(endpoints.admin.artworkSlot(date, position))

  // [MOCK]
  const raw = await adminMock.clearArtworkSlot(date, position)
  return {
    slot: toAdminSlot(raw.slot),
    exhibition: {
      version: raw.exhibition.version,
      canPublish: raw.exhibition.can_publish,
      publishBlockers: raw.exhibition.publish_blockers,
      isPublished: raw.exhibition.is_published,
      publishedNow: raw.exhibition.published_now,
    },
  }
}

/** `POST /admin/exhibitions/{date}/artworks/reorder` — 최종 상태 선언 */
export async function reorderArtworks(
  date: IsoDate,
  order: { artworkId: Uuid; position: number }[],
): Promise<AdminSlot[]> {
  // [API]
  // const raw = await httpClient.post<{ slots: RawAdminArtworkSlot[] }>(endpoints.admin.artworkReorder(date), {
  //   order: order.map((entry) => ({ artwork_id: entry.artworkId, position: entry.position })),
  // })
  // return raw.slots.map(toAdminSlot)

  // [MOCK]
  const raw = await adminMock.reorderArtworks(date, order)
  return raw.slots.map(toAdminSlot)
}

export type UploadTicket = {
  position: number
  artworkId: Uuid
  uploadUrl: string
  method: 'PUT'
  headers: Record<string, string>
  objectKey: string
  expiresAt: string
}

/**
 * `POST /admin/exhibitions/{date}/artworks/upload-urls` — Presigned URL 배치 발급
 * 20MB 파일은 API Gateway를 통과할 수 없으므로 클라이언트가 S3로 직접 올린다(PRD §9.2).
 */
export async function requestUploadUrls(
  date: IsoDate,
  files: { position: number; filename: string; contentType: string; sizeBytes: number; objectUrl?: string }[],
): Promise<UploadTicket[]> {
  // [API]
  // const raw = await httpClient.post<{ uploads: {...}[] }>(endpoints.admin.uploadUrls(date), {
  //   files: files.map((file) => ({
  //     position: file.position,
  //     filename: file.filename,
  //     content_type: file.contentType,
  //     size_bytes: file.sizeBytes,
  //   })),
  //   overwrite: false,
  // })
  // return raw.uploads.map((upload) => ({ ...camelCase 변환 }))

  // [MOCK]
  const raw = await adminMock.requestUploadUrls(date, files)
  return raw.uploads.map((upload) => ({
    position: upload.position,
    artworkId: upload.artwork_id,
    uploadUrl: upload.upload_url,
    method: upload.method,
    headers: upload.headers,
    objectKey: upload.object_key,
    expiresAt: upload.expires_at,
  }))
}

/** `POST /admin/artworks/{id}/image/complete` — S3 이벤트의 보조 경로 */
export async function completeImageUpload(artworkId: Uuid, objectKey: string): Promise<void> {
  // [API]
  // await httpClient.post(endpoints.admin.imageComplete(artworkId), { object_key: objectKey })

  // [MOCK]
  void objectKey
  await adminMock.completeImageUpload(artworkId)
}

/** `POST /admin/exhibitions/{date}/carry-draft` — 복사가 아니라 이동이다 */
export async function carryDraft(date: IsoDate): Promise<{ toDate: IsoDate; movedArtworkCount: number }> {
  // [API]
  // const raw = await httpClient.post<{ from_date: string; to_date: string; moved_artwork_count: number }>(
  //   endpoints.admin.exhibitionCarryDraft(date),
  //   { confirm: true },
  // )
  // return { toDate: raw.to_date, movedArtworkCount: raw.moved_artwork_count }

  // [MOCK]
  const raw = await adminMock.carryDraft(date)
  return { toDate: raw.to_date, movedArtworkCount: raw.moved_artwork_count }
}

/** `GET /admin/exhibitions/{date}/preview` — 관람자와 **동일한 스키마**를 준다 */
export async function fetchExhibitionPreview(date: IsoDate): Promise<Exhibition> {
  // [API]
  // const raw = await httpClient.get<RawExhibitionDetail>(endpoints.admin.exhibitionPreview(date))
  // return toExhibition(raw)

  // [MOCK]
  const raw = await adminMock.getExhibitionPreview(date)
  return toExhibition(raw)
}

/** `POST /admin/exhibitions/{date}/hide` · `/unhide` */
export async function setExhibitionHidden(date: IsoDate, hidden: boolean): Promise<void> {
  // [API]
  // await httpClient.post(
  //   hidden ? endpoints.admin.exhibitionHide(date) : endpoints.admin.exhibitionUnhide(date),
  //   hidden ? { reason: null } : undefined,
  // )

  // [MOCK]
  await adminMock.setExhibitionHidden(date, hidden)
}

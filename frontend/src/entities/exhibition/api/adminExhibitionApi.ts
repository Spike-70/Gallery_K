import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import { type CursorPage, toCursorPage } from '@/shared/api/pagination'
import type {
  RawAdminArtworkSlot,
  RawAdminExhibitionDay,
  RawAdminExhibitionDetail,
  RawAdminSummary,
  RawExhibitionDetail,
} from '@/shared/api/types'
import { CALENDAR_DEFAULT_DAYS } from '@/shared/config/constants'
import type { ImageStatus } from '@/shared/types/enums'
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

/** 서버가 저장 응답에 함께 실어 주는 전시 상태(API 문서 §9.5) */
type RawExhibitionState = {
  version: number
  can_publish: boolean
  publish_blockers: string[]
  is_published: boolean
  published_now: boolean
}

function toExhibitionState(raw: RawExhibitionState): SaveSlotResult['exhibition'] {
  return {
    version: raw.version,
    canPublish: raw.can_publish,
    publishBlockers: raw.publish_blockers,
    isPublished: raw.is_published,
    publishedNow: raw.published_now,
  }
}

/** `GET /admin/summary` — B 홈 요약(API 문서 §9.1) */
export async function fetchAdminSummary(): Promise<AdminSummary> {
  const raw = await httpClient.get<RawAdminSummary>(endpoints.admin.summary())
  return toAdminSummary(raw)
}

/** `GET /admin/exhibitions/calendar` — 범위의 모든 날짜가 빠짐없이 온다 */
export async function fetchCalendar(params: {
  direction?: 'future' | 'past'
  cursor?: string | null
  limit?: number
}): Promise<CursorPage<AdminExhibitionDay>> {
  const limit = params.limit ?? CALENDAR_DEFAULT_DAYS

  const { data, meta } = await httpClient.requestWithMeta<{ days: RawAdminExhibitionDay[] }>(
    endpoints.admin.calendar(),
    { query: { direction: params.direction, cursor: params.cursor ?? undefined, limit } },
  )
  return toCursorPage(data.days.map(toAdminDay), meta.pagination)
}

/** `GET /admin/exhibitions/{date}` — 행이 없어도 빈 12슬롯이 온다 */
export async function fetchAdminExhibition(date: IsoDate): Promise<AdminExhibition> {
  const raw = await httpClient.get<RawAdminExhibitionDetail>(endpoints.admin.exhibition(date))
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
  const raw = await httpClient.put<{
    exhibition_date: IsoDate
    version: number
    draft_updated_at: string | null
    is_published: boolean
    published_at: string | null
    can_publish: boolean
    publish_blockers: string[]
    published_now: boolean
  }>(endpoints.admin.exhibition(date), {
    title: input.title,
    theme: input.theme,
    version: input.version,
  })
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
  const raw = await httpClient.put<{ slot: RawAdminArtworkSlot; exhibition: RawExhibitionState }>(
    endpoints.admin.artworkSlot(date, position),
    {
      title: input.title,
      artist: input.artist,
      year_text: input.yearText,
      description: input.description,
      collection: input.collection,
      source_url: input.sourceUrl,
      version: input.version,
    },
  )
  return { slot: toAdminSlot(raw.slot), exhibition: toExhibitionState(raw.exhibition) }
}

/** `DELETE /admin/exhibitions/{date}/artworks/{position}` */
export async function clearArtworkSlot(date: IsoDate, position: number): Promise<SaveSlotResult> {
  const raw = await httpClient.delete<{
    slot: RawAdminArtworkSlot
    exhibition: RawExhibitionState
  }>(endpoints.admin.artworkSlot(date, position))
  return { slot: toAdminSlot(raw.slot), exhibition: toExhibitionState(raw.exhibition) }
}

/** `POST /admin/exhibitions/{date}/artworks/reorder` — 최종 상태 선언 */
export async function reorderArtworks(
  date: IsoDate,
  order: { artworkId: Uuid; position: number }[],
): Promise<AdminSlot[]> {
  const raw = await httpClient.post<{ slots: RawAdminArtworkSlot[] }>(
    endpoints.admin.artworkReorder(date),
    { order: order.map((entry) => ({ artwork_id: entry.artworkId, position: entry.position })) },
  )
  return raw.slots.map(toAdminSlot)
}

export type UploadTicket = {
  position: number
  artworkId: Uuid
  uploadUrl: string
  method: 'POST'
  /** 서명 정책 필드. **순서대로 폼에 담고 파일을 마지막에 붙인다**(API 문서 §9.8) */
  fields: Record<string, string>
  objectKey: string
  expiresAt: string
}

/**
 * `POST /admin/exhibitions/{date}/artworks/upload-urls` — presigned POST 자격 배치 발급
 * 20MB 파일은 API Gateway를 통과할 수 없으므로 클라이언트가 S3로 직접 올린다.
 *
 * 서버 스키마는 모르는 필드를 거부한다. **여기 적힌 네 필드 외에는 보내지 않는다.**
 */
export async function requestUploadUrls(
  date: IsoDate,
  files: { position: number; filename: string; contentType: string; sizeBytes: number }[],
): Promise<UploadTicket[]> {
  const raw = await httpClient.post<{
    uploads: {
      position: number
      artwork_id: Uuid
      upload_url: string
      method: 'POST'
      fields: Record<string, string>
      object_key: string
      expires_at: string
    }[]
  }>(endpoints.admin.uploadUrls(date), {
    files: files.map((file) => ({
      position: file.position,
      filename: file.filename,
      content_type: file.contentType,
      size_bytes: file.sizeBytes,
    })),
    overwrite: false,
  })
  return raw.uploads.map((upload) => ({
    position: upload.position,
    artworkId: upload.artwork_id,
    uploadUrl: upload.upload_url,
    method: upload.method,
    fields: upload.fields,
    objectKey: upload.object_key,
    expiresAt: upload.expires_at,
  }))
}

/**
 * `POST /admin/artworks/{id}/image/complete` — 업로드 완료 통지
 *
 * 서버가 **이 요청 안에서 동기로** 이미지를 변환하고 결과 상태로 응답한다(API 문서 §9.9).
 * 응답이 곧 처리 완료 통지이므로 화면은 폴링하지 않는다.
 */
export async function completeImageUpload(artworkId: Uuid, objectKey: string): Promise<ImageStatus> {
  const raw = await httpClient.post<{ image_status: ImageStatus }>(
    endpoints.admin.imageComplete(artworkId),
    { object_key: objectKey },
  )
  return raw.image_status
}

/** `POST /admin/exhibitions/{date}/carry-draft` — 복사가 아니라 이동이다 */
export async function carryDraft(
  date: IsoDate,
): Promise<{ toDate: IsoDate; movedArtworkCount: number }> {
  const raw = await httpClient.post<{
    from_date: IsoDate
    to_date: IsoDate
    moved_artwork_count: number
  }>(endpoints.admin.exhibitionCarryDraft(date), { confirm: true })
  return { toDate: raw.to_date, movedArtworkCount: raw.moved_artwork_count }
}

/** `GET /admin/exhibitions/{date}/preview` — 관람자와 **동일한 스키마**를 준다 */
export async function fetchExhibitionPreview(date: IsoDate): Promise<Exhibition> {
  const raw = await httpClient.get<RawExhibitionDetail>(endpoints.admin.exhibitionPreview(date))
  return toExhibition(raw)
}

/** `POST /admin/exhibitions/{date}/hide` · `/unhide` */
export async function setExhibitionHidden(date: IsoDate, hidden: boolean): Promise<void> {
  await httpClient.post(
    hidden ? endpoints.admin.exhibitionHide(date) : endpoints.admin.exhibitionUnhide(date),
    // `unhide`는 바디를 받지 않는다.
    hidden ? { reason: null } : undefined,
  )
}

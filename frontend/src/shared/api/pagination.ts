import type { PaginationMeta } from '@/shared/api/envelope'

/**
 * 페이지네이션 어댑터 — API 명세서 §2.4
 * 항목이 30개뿐인 목록도 동일한 규약을 따른다(AP-5). 목록 훅이 하나로 유지된다.
 */

export type CursorPage<T> = {
  items: T[]
  nextCursor: string | null
  hasMore: boolean
}

export type NumberedPage<T> = {
  items: T[]
  page: number
  totalCount: number
  totalPages: number
  hasMore: boolean
}

export function toCursorPage<T>(items: T[], meta: PaginationMeta | null | undefined): CursorPage<T> {
  return {
    items,
    nextCursor: meta?.has_more ? (meta.next_cursor ?? null) : null,
    hasMore: meta?.has_more ?? false,
  }
}

export function toNumberedPage<T>(items: T[], meta: PaginationMeta | null | undefined): NumberedPage<T> {
  return {
    items,
    page: meta?.page ?? 1,
    totalCount: meta?.total_count ?? items.length,
    totalPages: meta?.total_pages ?? 1,
    hasMore: meta?.has_more ?? false,
  }
}

/** 목 데이터에서 커서 페이지를 흉내 낸다. 커서는 불투명 문자열이다. */
export function paginateWithCursor<T>(items: T[], limit: number, cursor?: string | null): {
  page: CursorPage<T>
  meta: PaginationMeta
} {
  const offset = cursor ? Number(atob(cursor)) : 0
  const slice = items.slice(offset, offset + limit)
  const nextOffset = offset + slice.length
  const hasMore = nextOffset < items.length
  return {
    page: { items: slice, nextCursor: hasMore ? btoa(String(nextOffset)) : null, hasMore },
    meta: {
      mode: 'cursor',
      limit,
      count: slice.length,
      has_more: hasMore,
      next_cursor: hasMore ? btoa(String(nextOffset)) : null,
      page: null,
      total_count: null,
      total_pages: null,
    },
  }
}

/** 목 데이터에서 번호 페이지를 흉내 낸다. */
export function paginateWithPage<T>(items: T[], limit: number, page: number): {
  page: NumberedPage<T>
  meta: PaginationMeta
} {
  const totalPages = Math.max(1, Math.ceil(items.length / limit))
  const current = Math.min(Math.max(1, page), totalPages)
  const slice = items.slice((current - 1) * limit, current * limit)
  return {
    page: {
      items: slice,
      page: current,
      totalCount: items.length,
      totalPages,
      hasMore: current < totalPages,
    },
    meta: {
      mode: 'page',
      limit,
      count: slice.length,
      has_more: current < totalPages,
      next_cursor: null,
      page: current,
      total_count: items.length,
      total_pages: totalPages,
    },
  }
}

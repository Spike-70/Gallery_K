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

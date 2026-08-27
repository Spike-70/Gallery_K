import type { IsoDate } from '@/shared/types/utility'

/** 관리자 전시 쿼리 키 — 저장 후 `['admin']` 접두 무효화로 달력까지 갱신된다 */
export const adminExhibitionKeys = {
  all: ['admin'] as const,
  summary: () => ['admin', 'summary'] as const,
  calendar: (params: { direction: 'future' | 'past' }) => ['admin', 'calendar', params] as const,
  exhibition: (date: IsoDate) => ['admin', 'exhibition', date] as const,
  preview: (date: IsoDate) => ['admin', 'preview', date] as const,
}

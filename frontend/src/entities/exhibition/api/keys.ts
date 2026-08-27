import type { IsoDate } from '@/shared/types/utility'

/**
 * 전시 쿼리 키 — 프런트엔드 아키텍처 문서 §7.3
 * 무효화는 접두 매칭으로 한다. `['exhibition']`을 무효화하면 관련 화면이 모두 갱신된다.
 */
export const exhibitionKeys = {
  all: ['exhibition'] as const,
  current: () => ['exhibition', 'current'] as const,
  byDate: (date: IsoDate) => ['exhibition', 'date', date] as const,
  archive: (params: { limit: number }) => ['exhibition', 'archive', params] as const,
  preview: (date: IsoDate) => ['exhibition', 'preview', date] as const,
}

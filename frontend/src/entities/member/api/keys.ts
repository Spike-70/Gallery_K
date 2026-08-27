import type { Uuid } from '@/shared/types/utility'

export type MemberListParams = {
  query?: string
  status?: 'all' | 'active' | 'blocked'
  notify?: 'all' | 'on' | 'off'
  sort?: string
  page?: number
}

/** 관리자 쿼리 키 — 접두 `['admin']` 무효화로 관련 화면이 한 번에 갱신된다 */
export const memberKeys = {
  all: ['admin', 'members'] as const,
  list: (params: MemberListParams) => ['admin', 'members', params] as const,
  stats: (id: Uuid, days: number) => ['admin', 'stats', 'member', id, days] as const,
}

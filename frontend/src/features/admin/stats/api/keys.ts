/**
 * 통계 쿼리 키 — 프런트엔드 아키텍처 문서 §7.3
 *
 * **문자열 배열을 사용처에서 조립하지 않는다.** 조립이 흩어지면 무효화 접두가
 * 어긋나고, 어긋난 무효화는 조용히 오래된 화면을 남긴다.
 */
import type { Uuid } from '@/shared/types/utility'

export const statsKeys = {
  all: ['admin', 'stats'] as const,
  daily: (days: number) => ['admin', 'stats', 'daily', days] as const,
  memberSearch: (query: string) => ['admin', 'stats', 'search', query] as const,
  member: (memberId: Uuid, days: number) => ['admin', 'stats', 'member', memberId, days] as const,
}

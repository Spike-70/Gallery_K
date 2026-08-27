import type { Uuid } from '@/shared/types/utility'

/** 그림 쿼리 키 — 무효화는 접두 매칭으로 한다(프런트 §7.3) */
export const artworkKeys = {
  all: ['artwork'] as const,
  detail: (id: Uuid) => ['artwork', 'detail', id] as const,
}

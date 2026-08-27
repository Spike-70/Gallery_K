import { QueryClient } from '@tanstack/react-query'

import { isApiError } from '@/shared/api/ApiError'

/**
 * QueryClient 기본 옵션 — 프런트엔드 아키텍처 문서 §6.3
 *
 * 전역 기본값: 네트워크·5xx만 2회 재시도(지수 백오프 300ms → 1.2s),
 * 4xx는 재시도하지 않는다. `throwOnError`는 라우트 경계에서만 켠다.
 */

/** 도메인별 캐시 정책. 사용처가 숫자를 직접 쓰지 않게 한다. */
export const CACHE_POLICY = {
  /** 하루 단위로 바뀌는 데이터 */
  landing: { staleTime: 60_000, gcTime: 10 * 60_000 },
  currentExhibition: { staleTime: 5 * 60_000, gcTime: 24 * 3600_000 },
  /** 과거 전시는 불변이다 */
  pastExhibition: { staleTime: Infinity, gcTime: 24 * 3600_000 },
  archive: { staleTime: 5 * 60_000, gcTime: 3600_000 },
  artwork: { staleTime: Infinity, gcTime: 24 * 3600_000 },
  me: { staleTime: 5 * 60_000, gcTime: 3600_000 },
  /** 운영 데이터는 항상 최신 */
  admin: { staleTime: 0, gcTime: 5 * 60_000 },
  stats: { staleTime: 60_000, gcTime: 10 * 60_000 },
} as const

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false
  if (isApiError(error)) {
    // 4xx는 재시도해도 결과가 같다.
    if (error.status >= 400 && error.status < 500) return false
    return error.retryable || error.status === 0 || error.status >= 500
  }
  return true
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        retryDelay: (attempt) => Math.min(300 * 4 ** attempt, 1200),
        refetchOnWindowFocus: false,
        throwOnError: false,
        staleTime: 30_000,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

import { ApiError } from '@/shared/api/ApiError'
import { fallbackMessageFor } from '@/shared/api/errorMessages'
import { env } from '@/shared/config/env'

/**
 * 목 응답 유틸 — 데모 전용
 * 실제 네트워크의 지연·실패를 흉내 내어 로딩·오류 상태가 화면에서 실제로 관찰되게 한다.
 */

const DEFAULT_DELAY_MS = 260

/** 데모 스위치가 꺼진 채로 목 경로가 호출되면 즉시 드러나게 한다. */
function assertMockEnabled(): void {
  if (!env.useMock) {
    throw new Error('[mock] VITE_USE_MOCK=false 인데 목 핸들러가 호출되었습니다. 실제 API로 교체하세요.')
  }
}

export function mockDelay<T>(value: T, delayMs = DEFAULT_DELAY_MS): Promise<T> {
  assertMockEnabled()
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), delayMs)
  })
}

/** 오류 응답을 흉내 낸다. 화면의 오류 분기를 데모에서 확인할 수 있다. */
export function mockFail(code: string, status = 400, extra?: Partial<ConstructorParameters<typeof ApiError>[0]>): never {
  assertMockEnabled()
  throw new ApiError({
    code,
    message: fallbackMessageFor(code),
    status,
    retryable: false,
    requestId: `mock-${Date.now().toString(36)}`,
    ...extra,
  })
}

/** 결정적 난수 — 시드가 같으면 항상 같은 값이 나온다(스냅샷 안정). */
export function seededRandom(seed: number): () => number {
  let state = seed || 1
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296
    return state / 4294967296
  }
}

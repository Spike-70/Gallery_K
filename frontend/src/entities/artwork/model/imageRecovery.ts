import { logger } from '@/shared/lib/logger'

/**
 * 이미지 URL 복구 — 프런트엔드 아키텍처 문서 §8.2 (F-12)
 *
 * 이미지 URL은 만료가 있는 presigned URL이다(API 문서 §6.10). 만료되면
 * **모든 이미지가 한꺼번에 실패한다.** 단일 실패 지점이므로 복구 경로가 필요하다.
 *
 * 화면이 만료를 알아채는 유일한 신호는 "이미지가 계속 실패한다"뿐이다.
 * 그래서 실패를 세다가 **연속 3회**가 되면 복구를 1회 강제한다. 성공한 이미지가
 * 하나라도 있으면 세던 것을 버린다 — 한 장이 깨진 것과 전부가 깨진 것은 다른 사건이다.
 *
 * 복구 수단은 **그림을 담은 쿼리를 무효화해 새 URL을 받는 것**이며, 주입은 앱 셸이 한다.
 * 이미지 컴포넌트는 "실패했다"만 알리고 무엇을 할지는 모른다.
 */
const FAILURE_THRESHOLD = 3

let consecutiveFailures = 0
let recovering = false
let recover: (() => Promise<void>) | null = null

/** 앱 부팅 시 `QueryProvider`가 복구 수단을 주입한다. */
export function registerImageRecovery(handler: () => Promise<void>): void {
  recover = handler
}

export function reportImageSuccess(): void {
  consecutiveFailures = 0
}

/** @returns 복구를 시도했는가. 시도했다면 호출부가 이미지를 다시 걸어 볼 만하다. */
export function reportImageFailure(): boolean {
  consecutiveFailures += 1
  if (consecutiveFailures < FAILURE_THRESHOLD || recovering || !recover) return false

  recovering = true
  consecutiveFailures = 0
  void recover()
    .catch((error: unknown) => logger.warn('image url recovery failed', error))
    .finally(() => {
      recovering = false
    })
  return true
}

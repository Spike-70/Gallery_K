import { logger } from '@/shared/lib/logger'

/**
 * 미디어 쿠키 복구 — 프런트엔드 아키텍처 문서 §8.2 (F-12)
 *
 * 서명 쿠키가 만료되면 **모든 이미지가 한꺼번에 403**이 된다. 단일 실패 지점이다.
 * 타이머 갱신이 어떤 이유로든 놓친 경우, 화면이 그것을 알아채는 유일한 신호는
 * "이미지가 계속 실패한다"뿐이다.
 *
 * 그래서 이미지 실패를 세다가 **연속 3회**가 되면 쿠키 갱신을 1회 강제한다.
 * 성공한 이미지가 하나라도 있으면 세던 것을 버린다 — 한 장이 깨진 것과
 * 전부가 깨진 것은 다른 사건이다.
 *
 * `entities/session`이 소유하는 이유: 복구 수단이 세션의 것이기 때문이다.
 * 이미지 컴포넌트는 "실패했다"만 알리고 무엇을 할지는 모른다.
 */
const FAILURE_THRESHOLD = 3

let consecutiveFailures = 0
let recovering = false
let recover: (() => Promise<void>) | null = null

/** 앱 부팅 시 `SessionProvider`가 복구 수단을 주입한다. */
export function registerMediaRecovery(handler: () => Promise<void>): void {
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
    .catch((error: unknown) => logger.warn('media session recovery failed', error))
    .finally(() => {
      recovering = false
    })
  return true
}

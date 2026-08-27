import { logger } from '@/shared/lib/logger'

/**
 * 서비스워커 등록 — 프런트엔드 아키텍처 문서 §10.2
 *
 * **새 버전을 자동으로 적용하지 않는다.** 대기 중인 워커가 생기면 구독자에게 알리고,
 * 사용자가 `새로고침`을 누를 때만 교체한다 — 그림을 보는 도중 화면이 리로드되면
 * 그것만으로 이 제품의 약속이 깨진다.
 *
 * React를 모른다. 화면 쪽 결합은 `PwaProvider`가 갖는다.
 */

type UpdateListener = (updateReady: boolean) => void

let updateReady = false
let applyUpdate: (() => void) | null = null
let registered = false
const listeners = new Set<UpdateListener>()

function emit() {
  for (const listener of listeners) listener(updateReady)
}

/** 대기 중인 새 버전 유무를 구독한다. `useSyncExternalStore`가 요구하는 형태다. */
export function subscribeToUpdates(listener: UpdateListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function isUpdateReady(): boolean {
  return updateReady
}

/** 대기 중인 워커를 적용하고 페이지를 새로 띄운다. 사용자가 명시적으로 누를 때만 부른다. */
export function activateUpdate(): void {
  applyUpdate?.()
}

/**
 * 부팅당 1회 등록한다. 서비스워커를 지원하지 않는 환경(테스트·구형 브라우저)에서는
 * 아무 일도 하지 않으며, 화면은 평소와 똑같이 동작한다(FA-7).
 */
export function registerServiceWorker(): void {
  if (registered) return
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return
  registered = true

  // `virtual:pwa-register`는 빌드 타임 가상 모듈이다. 정적 import 하면 테스트 환경이
  // 해석하지 못하므로 실제로 등록할 때만 가져온다.
  void import('virtual:pwa-register')
    .then(({ registerSW }) => {
      applyUpdate = registerSW({
        immediate: true,
        onNeedRefresh() {
          updateReady = true
          emit()
        },
        onRegisterError(error: unknown) {
          logger.warn('service worker registration failed', error)
        },
      })
    })
    .catch((error: unknown) => {
      logger.warn('service worker module unavailable', error)
    })
}

/**
 * 서비스워커가 보내는 메시지를 구독한다.
 * 지금은 `pushsubscriptionchange`(브라우저가 구독을 스스로 교체한 경우) 하나뿐이다.
 */
export function subscribeToWorkerMessages(handler: (type: string) => void): () => void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return () => {}

  const listener = (event: MessageEvent) => {
    const type = (event.data as { type?: string } | null)?.type
    if (type) handler(type)
  }
  navigator.serviceWorker.addEventListener('message', listener)
  return () => navigator.serviceWorker.removeEventListener('message', listener)
}

import { useEffect, useSyncExternalStore } from 'react'
import { createPortal } from 'react-dom'

import {
  activateUpdate,
  isUpdateReady,
  registerServiceWorker,
  subscribeToUpdates,
  subscribeToWorkerMessages,
} from '@/app/pwa/serviceWorkerRegistry'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { usePushSubscription } from '@/features/notification'
import { actions, status } from '@/shared/config/messages'
import { logger } from '@/shared/lib/logger'
import { Banner, Button } from '@/shared/ui'

/**
 * PWA 런타임 — 프런트엔드 아키텍처 문서 §10
 *
 * 세 가지를 앱 셸에 한 번씩만 붙인다.
 *  1. 서비스워커 등록(§10.2)
 *  2. 새 버전 안내 바 — **자동 갱신하지 않는다**
 *  3. 푸시 구독 재검증 — **부팅당 1회**, 로그인 상태에서만(§10.3)
 *
 * 화면은 이 프로바이더가 없어도 전부 동작한다. 서비스워커를 지원하지 않는
 * 브라우저에서 아무 일도 일어나지 않는 것이 정상이다(FA-7).
 */

/** 대기 중인 새 버전 안내. 하단에 조용히 뜬다(§10.2). */
function UpdateBanner() {
  const updateReady = useSyncExternalStore(subscribeToUpdates, isUpdateReady, () => false)

  if (!updateReady) return null

  return createPortal(
    <div className="fixed bottom-0 left-0 right-0 z-sticky">
      <Banner
        tone="update"
        message={status.updateAvailable}
        className="border-b-0 border-t shadow-dialog"
        action={
          <Button size="sm" variant="ghost" onClick={activateUpdate}>
            {actions.refresh}
          </Button>
        }
      />
    </div>,
    document.body,
  )
}

/**
 * 브라우저 구독과 서버 등록 목록을 대조한다.
 * 로그인한 뒤 한 번만 돈다 — 익명 상태에서 `/me/push-subscriptions`를 부르지 않는다.
 */
function usePushReconciliation() {
  const sessionStatus = useSessionStore((state) => state.status)
  const { reconcile } = usePushSubscription()

  useEffect(() => {
    if (sessionStatus !== 'authenticated') return

    let done = false
    const run = () => {
      if (done) return
      done = true
      reconcile().catch((error: unknown) => logger.warn('push reconcile failed', error))
    }
    run()

    // 브라우저가 구독을 스스로 교체하면 워커가 알려준다(§10.4).
    return subscribeToWorkerMessages((type) => {
      if (type !== 'PUSH_SUBSCRIPTION_CHANGED') return
      done = false
      run()
    })
  }, [sessionStatus, reconcile])
}

export function PwaProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    registerServiceWorker()
  }, [])

  usePushReconciliation()

  return (
    <>
      {children}
      <UpdateBanner />
    </>
  )
}

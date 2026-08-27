import { useCallback, useState } from 'react'

import * as pushApi from '@/features/notification/api/pushApi'
import * as pushClient from '@/features/notification/lib/pushClient'
import { screens } from '@/shared/config/messages'
import { needsIosInstallGuide } from '@/shared/lib/platform'
import { toast } from '@/shared/ui'

/**
 * 푸시 구독 흐름 — 프런트엔드 아키텍처 문서 §10.3
 *
 * 1. iOS이고 standalone이 아니면 **홈 화면 추가 안내를 먼저** 보여준다. 권한을 요청하지 않는다.
 * 2. `Notification.requestPermission()`
 * 3. 허용 시 구독 → `POST /me/push-subscriptions`
 * 4. **거부되면 다시 묻지 않는다.**
 */
export type EnableResult = 'enabled' | 'needs-ios-guide' | 'denied' | 'failed'

export function usePushSubscription() {
  const [pending, setPending] = useState(false)

  const enable = useCallback(async (): Promise<EnableResult> => {
    if (needsIosInstallGuide()) return 'needs-ios-guide'

    setPending(true)
    try {
      const permission = await pushClient.requestPermission()
      if (permission !== 'granted') return 'denied'

      const subscription = await pushClient.subscribe()
      if (!subscription) {
        toast.error(screens.settings.notifyFailed)
        return 'failed'
      }

      await pushApi.registerPushSubscription(subscription)
      return 'enabled'
    } catch {
      toast.error(screens.settings.notifyFailed)
      return 'failed'
    } finally {
      setPending(false)
    }
  }, [])

  /**
   * 구독 재검증 — 브라우저의 현재 구독과 서버 등록 목록을 대조한다.
   * **부팅당 1회**만 수행한다.
   */
  const reconcile = useCallback(async (): Promise<void> => {
    if (pushClient.currentPermission() !== 'granted') return
    const [browser, server] = await Promise.all([pushClient.subscribe(), pushApi.fetchPushSubscriptions()])
    if (!browser) return
    const known = server.some((item) => item.endpointHash === browser.endpointHash && item.isActive)
    if (!known) await pushApi.registerPushSubscription(browser)
  }, [])

  return { enable, reconcile, pending, permission: pushClient.currentPermission() }
}

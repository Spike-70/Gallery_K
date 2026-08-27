import { useState } from 'react'

import { IosInstallGuide } from '@/features/notification/components/IosInstallGuide'
import { usePushSubscription } from '@/features/notification/hooks/usePushSubscription'
import { actions, screens } from '@/shared/config/messages'
import { STORAGE_KEYS, localStore } from '@/shared/lib/storage'
import { Button } from '@/shared/ui'

/**
 * 알림 권한 안내 — UX 설계서 §3.3
 *
 * 가입 완료 직후 전체 화면 오버레이로 한 번 보여준다.
 * `나중에`를 누르면 **다시 묻지 않는다.** C-4 설정에서 언제든 켤 수 있다.
 */
export type PushPermissionPromptProps = {
  onDone: () => void
}

/**
 * 이미 한 번 물어봤는가. `나중에`를 누른 사람에게 **다시 묻지 않기 위해** 쓴다(UX §3.3).
 * 이 판단은 프롬프트를 띄우려는 쪽이 한다.
 */
export function hasAskedNotifyPermission(): boolean {
  return localStore.get(STORAGE_KEYS.notifyPromptSeen) === '1'
}

export function PushPermissionPrompt({ onDone }: PushPermissionPromptProps) {
  const { enable, pending } = usePushSubscription()
  const [showIosGuide, setShowIosGuide] = useState(false)

  const finish = () => {
    localStore.set(STORAGE_KEYS.notifyPromptSeen, '1')
    onDone()
  }

  const handleAllow = async () => {
    const result = await enable()
    if (result === 'needs-ios-guide') {
      setShowIosGuide(true)
      return
    }
    finish()
  }

  return (
    <div className="fixed inset-0 z-dialog flex items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-form">
        {showIosGuide ? (
          <IosInstallGuide onClose={finish} />
        ) : (
          <div className="flex flex-col items-center gap-6 text-center">
            <h2 className="text-title-md text-primary">{screens.notifyPrompt.title}</h2>
            <p className="gk-prose text-center text-body-md text-secondary">{screens.notifyPrompt.body}</p>
            <div className="flex w-full flex-col items-center gap-2">
              <Button size="lg" block loading={pending} onClick={() => void handleAllow()}>
                {actions.allowNotification}
              </Button>
              <Button variant="ghost" size="md" block onClick={finish}>
                {actions.later}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

import { useState } from 'react'

import type { SessionUser } from '@/entities/session/model/types'
import { IosInstallGuide, usePushSubscription } from '@/features/notification'
import { NOTIFY_HOUR_RANGE } from '@/shared/config/constants'
import { screens } from '@/shared/config/messages'
import { timeOptions } from '@/shared/lib/date'
import { needsIosInstallGuide } from '@/shared/lib/platform'
import { BottomSheet, Divider, Switch, TextButton, TimeSelectSheet } from '@/shared/ui'

/**
 * 알림 섹션 — UX 설계서 §3.10
 *
 * **1탭으로 꺼진다. 붙잡지 않는다.** 알림 시각은 켜져 있을 때만 노출하며
 * 드럼이 아닌 목록 선택 시트로 고른다(S-10).
 */
export type NotifySectionProps = {
  user: SessionUser
  onChange: (patch: { notifyEnabled?: boolean; notifyAt?: string }) => void
}

export function NotifySection({ user, onChange }: NotifySectionProps) {
  const { enable, permission } = usePushSubscription()
  const [timeSheetOpen, setTimeSheetOpen] = useState(false)
  const [iosGuideOpen, setIosGuideOpen] = useState(false)

  const blockedByBrowser = permission === 'denied'
  const needsInstall = needsIosInstallGuide()

  const handleToggle = async (checked: boolean) => {
    if (!checked) {
      onChange({ notifyEnabled: false })
      return
    }
    const result = await enable()
    if (result === 'needs-ios-guide') {
      setIosGuideOpen(true)
      return
    }
    if (result === 'enabled') onChange({ notifyEnabled: true })
  }

  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-label text-tertiary">{screens.settings.notifySection}</h2>

      {needsInstall ? (
        <div className="flex flex-col gap-2 py-2">
          <p className="text-body-md text-secondary">{screens.settings.notifyIosGuide}</p>
          <TextButton tone="accent" onClick={() => setIosGuideOpen(true)}>
            {screens.settings.notifyIosGuideOpen}
          </TextButton>
        </div>
      ) : (
        <Switch
          label={screens.settings.notifyToggle}
          description={blockedByBrowser ? screens.settings.notifyDenied : undefined}
          checked={user.notifyEnabled}
          disabled={blockedByBrowser}
          onCheckedChange={(checked) => void handleToggle(checked)}
        />
      )}

      {user.notifyEnabled && !needsInstall ? (
        <>
          <Divider />
          <button
            type="button"
            onClick={() => setTimeSheetOpen(true)}
            className="flex min-h-touch items-center justify-between px-1 text-left"
          >
            <span className="text-body-md text-primary">{screens.settings.notifyTime}</span>
            <span className="tabular text-body-md text-secondary">{user.notifyAt}</span>
          </button>
        </>
      ) : null}

      <TimeSelectSheet
        open={timeSheetOpen}
        title={screens.settings.notifyTimeSheetTitle}
        value={user.notifyAt}
        options={timeOptions(NOTIFY_HOUR_RANGE.start, NOTIFY_HOUR_RANGE.end, NOTIFY_HOUR_RANGE.stepMinutes)}
        onSelect={(notifyAt) => onChange({ notifyAt })}
        onClose={() => setTimeSheetOpen(false)}
      />

      <BottomSheet
        open={iosGuideOpen}
        title={screens.settings.notifyIosGuide}
        onClose={() => setIosGuideOpen(false)}
      >
        <IosInstallGuide onClose={() => setIosGuideOpen(false)} />
      </BottomSheet>
    </section>
  )
}

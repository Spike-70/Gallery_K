import { useState } from 'react'

import { useWithdraw } from '@/features/settings/hooks/useWithdraw'
import { actions, screens } from '@/shared/config/messages'
import { Dialog, TextButton } from '@/shared/ui'

/**
 * 탈퇴 — UX 설계서 §3.10 (UX-6)
 * 맨 아래에 작게 둔다. 되돌릴 수 없다는 사실을 명확히 알리고 확인은 한 번만 받는다.
 */
export function WithdrawSection() {
  const [open, setOpen] = useState(false)
  const mutation = useWithdraw()

  return (
    <section className="flex justify-center pt-4">
      <TextButton tone="danger" onClick={() => setOpen(true)}>
        {screens.settings.withdrawLink}
      </TextButton>

      <Dialog
        open={open}
        title={screens.settings.withdrawTitle}
        description={screens.settings.withdrawBody}
        confirmLabel={actions.confirmWithdraw}
        destructive
        loading={mutation.isPending}
        onConfirm={() => mutation.mutate()}
        onClose={() => setOpen(false)}
      />
    </section>
  )
}

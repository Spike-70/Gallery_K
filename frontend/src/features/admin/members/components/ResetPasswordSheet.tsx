import { useState } from 'react'

import { useResetMemberPasswordMutation } from '@/entities/member/api/queries'
import type { Member } from '@/entities/member/model/types'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screens } from '@/shared/config/messages'
import { AlertDialog, BottomSheet, Button, FieldGroup, TextField } from '@/shared/ui'

/**
 * 비밀번호 초기화 — UX 설계서 §3.15
 *
 * 회원의 모든 세션이 무효화되고 `must_change_password=true`가 된다.
 * 큐레이터가 **전화로 새 비밀번호를 전달하는 운영 흐름**을 전제하므로,
 * 완료 후 전달할 문구를 그대로 보여준다(PRD §6.14).
 */
export function ResetPasswordSheet({ member, onClose }: { member: Member | null; onClose: () => void }) {
  const mutation = useResetMemberPasswordMutation()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)

  const submit = async () => {
    if (!member) return
    setError(null)
    try {
      await mutation.mutateAsync({ id: member.id, newPassword: password })
      setDone(screens.members.resetPasswordDone(member.name, password))
      setPassword('')
      onClose()
    } catch (caught) {
      setError(resolveErrorMessage(caught))
    }
  }

  return (
    <>
      <BottomSheet
        open={Boolean(member)}
        title={member ? screens.members.resetPasswordTitle(member.name) : ''}
        onClose={onClose}
      >
        <div className="flex flex-col gap-5 pb-4">
          <p className="text-body-sm text-secondary">{screens.members.resetPasswordBody}</p>

          {error ? (
            <p role="alert" className="text-caption text-danger">
              {error}
            </p>
          ) : null}

          <FieldGroup
            id="reset-member-password"
            label={screens.members.initialPasswordLabel}
            hint={screens.signup.passwordHint}
            required
          >
            <TextField
              id="reset-member-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </FieldGroup>

          <Button size="lg" block loading={mutation.isPending} onClick={() => void submit()}>
            {actions.resetPassword}
          </Button>
        </div>
      </BottomSheet>

      <AlertDialog open={Boolean(done)} title={done ?? ''} onClose={() => setDone(null)} />
    </>
  )
}

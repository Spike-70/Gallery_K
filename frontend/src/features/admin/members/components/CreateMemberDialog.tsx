import { useState } from 'react'

import { useCreateMemberMutation } from '@/entities/member/api/queries'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { LIMITS } from '@/shared/config/constants'
import { actions, screens } from '@/shared/config/messages'
import { formatPhone, normalizePhone } from '@/shared/lib/phone'
import { AlertDialog, BottomSheet, Button, FieldGroup, TextField } from '@/shared/ui'

/**
 * 대행 가입 — UX 설계서 §3.15
 *
 * 생성 후 **안내 카드**를 띄운다. 큐레이터가 전화로 초기 비밀번호를 전달하는
 * 운영 흐름을 전제한다(PRD §6.14). 계정은 `must_change_password=true`로 만들어진다.
 */
export function CreateMemberDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const mutation = useCreateMemberMutation()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<{ name: string; phone: string; password: string } | null>(null)

  const submit = async () => {
    setError(null)
    try {
      await mutation.mutateAsync({ name, phone: normalizePhone(phone), initialPassword: password })
      setCreated({ name, phone: formatPhone(phone), password })
      setName('')
      setPhone('')
      setPassword('')
      onClose()
    } catch (caught) {
      setError(resolveErrorMessage(caught))
    }
  }

  return (
    <>
      <BottomSheet open={open} title={screens.members.createTitle} onClose={onClose}>
        <div className="flex flex-col gap-5 pb-4">
          {error ? (
            <p role="alert" className="text-caption text-danger">
              {error}
            </p>
          ) : null}

          <FieldGroup id="member-name" label={screens.settings.nameLabel} required>
            <TextField
              id="member-name"
              maxLength={LIMITS.memberName}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </FieldGroup>

          <FieldGroup id="member-phone" label={screens.settings.phoneLabel} required>
            <TextField
              id="member-phone"
              type="tel"
              inputMode="numeric"
              maxLength={13}
              value={phone}
              onChange={(event) => setPhone(formatPhone(event.target.value))}
            />
          </FieldGroup>

          <FieldGroup
            id="member-password"
            label={screens.members.initialPasswordLabel}
            hint={screens.signup.passwordHint}
            required
          >
            <TextField
              id="member-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </FieldGroup>

          <Button size="lg" block loading={mutation.isPending} onClick={() => void submit()}>
            {actions.createAccount}
          </Button>
        </div>
      </BottomSheet>

      <AlertDialog
        open={Boolean(created)}
        title={created ? screens.members.createdTitle(created.name) : ''}
        description={
          created ? (
            <span className="flex flex-col gap-2">
              <span className="tabular">{screens.members.createdDetail(created.phone, created.password)}</span>
              <span>{screens.members.createdGuide}</span>
            </span>
          ) : undefined
        }
        onClose={() => setCreated(null)}
      />
    </>
  )
}

import { type ReactNode, forwardRef, useState } from 'react'

import { screens } from '@/shared/config/messages'
import { FieldGroup, IconButton, TextField, fieldIds } from '@/shared/ui'

/**
 * 비밀번호 입력 — UX 설계서 §3.2
 * 우측에 보기/숨기기 토글. 기본은 숨김이며 토글 버튼은 48×48px를 차지한다.
 */
export type PasswordFieldProps = {
  id?: string
  label: string
  hint?: ReactNode
  error?: string
  autoComplete: 'current-password' | 'new-password'
  disabled?: boolean
} & React.InputHTMLAttributes<HTMLInputElement>

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(function PasswordField(
  { id = 'password', label, hint, error, autoComplete, disabled, ...props },
  ref,
) {
  const [visible, setVisible] = useState(false)
  const { hintId, errorId } = fieldIds(id)

  return (
    <FieldGroup id={id} label={label} hint={hint} error={error} required>
      <TextField
        ref={ref}
        id={id}
        type={visible ? 'text' : 'password'}
        autoComplete={autoComplete}
        required
        disabled={disabled}
        invalid={Boolean(error)}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        trailing={
          <IconButton
            icon={visible ? 'eye-off' : 'eye'}
            label={visible ? screens.login.hidePassword : screens.login.showPassword}
            onClick={() => setVisible((current) => !current)}
            tabIndex={-1}
          />
        }
        {...props}
      />
    </FieldGroup>
  )
})

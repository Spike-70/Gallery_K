import { forwardRef } from 'react'

import { formatPhone } from '@/shared/lib/phone'
import { FieldGroup, TextField, fieldIds } from '@/shared/ui'

/**
 * 전화번호 입력 — UX 설계서 §3.2·§7
 * 숫자 키패드 · 입력 중 자동 하이픈 · 최대 13자(하이픈 포함) · `autocomplete="tel"`.
 */
export type PhoneFieldProps = {
  id?: string
  label: string
  hint?: string
  error?: string
  value: string
  onValueChange: (value: string) => void
  onBlur?: () => void
  disabled?: boolean
}

export const PhoneField = forwardRef<HTMLInputElement, PhoneFieldProps>(function PhoneField(
  { id = 'phone', label, hint, error, value, onValueChange, onBlur, disabled },
  ref,
) {
  const { hintId, errorId } = fieldIds(id)
  return (
    <FieldGroup id={id} label={label} hint={hint} error={error} required>
      <TextField
        ref={ref}
        id={id}
        type="tel"
        inputMode="numeric"
        autoComplete="tel"
        maxLength={13}
        required
        placeholder="010-0000-0000"
        value={value}
        disabled={disabled}
        invalid={Boolean(error)}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        onChange={(event) => onValueChange(formatPhone(event.target.value))}
        onBlur={onBlur}
      />
    </FieldGroup>
  )
})

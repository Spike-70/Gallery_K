import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import {
  usePasswordResetConfirmMutation,
  usePasswordResetRequestMutation,
} from '@/entities/session/api/queries'
import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { PhoneField } from '@/features/auth/components/PhoneField'
import {
  type PasswordResetConfirmForm,
  type PasswordResetRequestForm,
  passwordResetConfirmSchema,
  passwordResetRequestSchema,
} from '@/features/auth/model/schemas'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { applyApiError } from '@/shared/lib/formErrors'
import { normalizePhone } from '@/shared/lib/phone'
import { BackLink, Button, FieldGroup, TextField, toast } from '@/shared/ui'

/**
 * A-2. 비밀번호 재설정 *(v1.1)* — UX 설계서 §3.4
 *
 * 단계 1에서 **미가입 번호여도 단계 2로 넘어간다** — 계정 존재를 노출하지 않는다(PRD §6.2).
 * 완료 후 자동 로그인하지 않고 A-1으로 보낸다.
 */
export function PasswordResetPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState<string | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [bannerMessage, setBannerMessage] = useState<string | null>(null)

  const requestMutation = usePasswordResetRequestMutation()
  const confirmMutation = usePasswordResetConfirmMutation()

  const requestForm = useForm<PasswordResetRequestForm>({
    resolver: zodResolver(passwordResetRequestSchema),
    defaultValues: { phone: '' },
  })
  const confirmForm = useForm<PasswordResetConfirmForm>({
    resolver: zodResolver(passwordResetConfirmSchema),
    defaultValues: { code: '', newPassword: '' },
  })

  // 남은 시간 카운트다운 — `2:47` 형식
  useEffect(() => {
    if (remainingSeconds <= 0) return
    const timer = window.setInterval(() => setRemainingSeconds((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [remainingSeconds])

  const submitRequest = requestForm.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      const result = await requestMutation.mutateAsync({ phone: normalizePhone(values.phone) })
      setPhone(normalizePhone(values.phone))
      setRemainingSeconds(result.expiresInSeconds)
    } catch (error) {
      setBannerMessage(applyApiError(error, requestForm.setError))
    }
  })

  const submitConfirm = confirmForm.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      await confirmMutation.mutateAsync({ phone: phone ?? '', ...values })
      toast.info(screens.passwordReset.doneBanner)
      navigate(paths.login, { replace: true })
    } catch (error) {
      setBannerMessage(applyApiError(error, confirmForm.setError))
    }
  })

  const countdown = `${Math.floor(remainingSeconds / 60)}:${String(remainingSeconds % 60).padStart(2, '0')}`

  return (
    <div className="gk-container-form flex min-h-screen flex-col justify-center py-12">
      <h1 className="mb-6 text-center text-title-md text-primary">{screenTitles.passwordReset}</h1>

      {bannerMessage ? <FormBanner message={bannerMessage} className="mb-4" /> : null}

      {phone === null ? (
        <form onSubmit={submitRequest} noValidate className="flex flex-col gap-5">
          <p className="text-body-md text-secondary">{screens.passwordReset.step1Guide}</p>
          <Controller
            control={requestForm.control}
            name="phone"
            render={({ field, fieldState }) => (
              <PhoneField
                label={screens.login.phoneLabel}
                value={field.value}
                onValueChange={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                disabled={requestMutation.isPending}
              />
            )}
          />
          <Button type="submit" size="lg" block loading={requestMutation.isPending}>
            {actions.sendCode}
          </Button>
        </form>
      ) : (
        <form onSubmit={submitConfirm} noValidate className="flex flex-col gap-5">
          <FieldGroup
            id="reset-code"
            label={screens.passwordReset.codeLabel}
            hint={remainingSeconds > 0 ? countdown : screens.passwordReset.expired}
            error={confirmForm.formState.errors.code?.message}
            required
          >
            <TextField
              id="reset-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              invalid={Boolean(confirmForm.formState.errors.code)}
              {...confirmForm.register('code')}
            />
          </FieldGroup>

          <PasswordField
            id="reset-new-password"
            label={screens.passwordReset.newPasswordLabel}
            hint={screens.signup.passwordHint}
            autoComplete="new-password"
            error={confirmForm.formState.errors.newPassword?.message}
            {...confirmForm.register('newPassword')}
          />

          <Button type="submit" size="lg" block loading={confirmMutation.isPending}>
            {actions.changePassword}
          </Button>

          <Button
            variant="ghost"
            size="md"
            block
            disabled={remainingSeconds > 120}
            onClick={() => void submitRequest()}
          >
            {actions.resendCode}
          </Button>
        </form>
      )}

      <BackLink to={paths.landing} label={actions.backHome} />
    </div>
  )
}

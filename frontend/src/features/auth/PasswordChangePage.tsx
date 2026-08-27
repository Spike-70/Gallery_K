import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { useChangePasswordMutation, useLogoutMutation } from '@/entities/session/api/queries'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { type PasswordChangeForm, passwordChangeSchema } from '@/features/auth/model/schemas'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { applyApiError } from '@/shared/lib/formErrors'
import { BackLink, Button, TextButton, toast } from '@/shared/ui'

/**
 * 비밀번호 변경 — UX 설계서 §3.5
 *
 * 강제 진입(`mustChangePassword`)에서는 되돌아가기를 두지 않는다. **UX-3의 유일한 예외**이며,
 * 대신 `로그아웃` 링크로 갇히지 않게 한다(U-12).
 */
export function PasswordChangePage() {
  const navigate = useNavigate()
  const forced = useSessionStore((state) => state.user?.mustChangePassword ?? false)
  const mutation = useChangePasswordMutation()
  const logout = useLogoutMutation()
  const [bannerMessage, setBannerMessage] = useState<string | null>(null)

  const form = useForm<PasswordChangeForm>({
    resolver: zodResolver(passwordChangeSchema),
    mode: 'onBlur',
    defaultValues: { currentPassword: '', newPassword: '' },
  })

  const submit = form.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      await mutation.mutateAsync(values)
      toast.info(screens.passwordChange.done)
      navigate(paths.gallery, { replace: true })
    } catch (error) {
      setBannerMessage(applyApiError(error, form.setError))
    }
  })

  return (
    <div className="gk-container-form flex min-h-screen flex-col justify-center py-12">
      <h1 className="mb-4 text-center text-title-md text-primary">{screenTitles.passwordChange}</h1>

      {forced ? (
        <p className="mb-6 text-center text-body-md text-secondary">{screens.passwordChange.forcedGuide}</p>
      ) : null}

      {bannerMessage ? <FormBanner message={bannerMessage} className="mb-4" /> : null}

      <form onSubmit={submit} noValidate className="flex flex-col gap-5">
        <PasswordField
          id="current-password"
          label={screens.passwordChange.currentLabel}
          autoComplete="current-password"
          error={form.formState.errors.currentPassword?.message}
          disabled={mutation.isPending}
          {...form.register('currentPassword')}
        />
        <PasswordField
          id="new-password"
          label={screens.passwordChange.newLabel}
          hint={screens.signup.passwordHint}
          autoComplete="new-password"
          error={form.formState.errors.newPassword?.message}
          disabled={mutation.isPending}
          {...form.register('newPassword')}
        />
        <Button type="submit" size="lg" block loading={mutation.isPending}>
          {actions.changePassword}
        </Button>
      </form>

      {forced ? (
        <div className="flex justify-center py-8">
          <TextButton
            tone="tertiary"
            onClick={() =>
              logout.mutate(undefined, { onSuccess: () => navigate(paths.landing, { replace: true }) })
            }
          >
            {actions.logout}
          </TextButton>
        </div>
      ) : (
        <BackLink to={paths.settings} label={actions.backSettings} />
      )}
    </div>
  )
}

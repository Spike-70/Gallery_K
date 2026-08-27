import { Controller } from 'react-hook-form'

import { paths } from '@/shared/config/paths'
import { DemoAccountsNotice } from '@/features/auth/components/DemoAccountsNotice'
import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { PhoneField } from '@/features/auth/components/PhoneField'
import { useLogin } from '@/features/auth/hooks/useLogin'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { BackLink, Button, TextLink } from '@/shared/ui'

/** A-1. 로그인 — UX 설계서 §3.2 */
export function LoginPage() {
  const { form, submit, bannerMessage, isSubmitting } = useLogin()
  const { control, register, formState } = form

  return (
    <div className="gk-container-form flex min-h-screen flex-col justify-center py-12">
      <h1 className="mb-8 text-center text-title-md text-primary">{screenTitles.login}</h1>

      {bannerMessage ? <FormBanner message={bannerMessage} className="mb-4" /> : null}

      <form onSubmit={submit} noValidate className="flex flex-col gap-5">
        <Controller
          control={control}
          name="phone"
          render={({ field, fieldState }) => (
            <PhoneField
              label={screens.login.phoneLabel}
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
              disabled={isSubmitting}
            />
          )}
        />

        <PasswordField
          label={screens.login.passwordLabel}
          autoComplete="current-password"
          error={formState.errors.password?.message}
          disabled={isSubmitting}
          {...register('password')}
        />

        <Button type="submit" size="lg" block loading={isSubmitting}>
          {actions.login}
        </Button>
      </form>

      <div className="mt-6 flex justify-center">
        <TextLink to={paths.passwordReset} tone="tertiary">
          {screens.login.forgotPassword}
        </TextLink>
      </div>

      {/* [MOCK] 데모 계정 안내 — 실제 서비스에서는 이 한 줄만 지우면 된다. */}
      <DemoAccountsNotice />

      <BackLink to={paths.landing} label={actions.backHome} />
    </div>
  )
}

import { Controller } from 'react-hook-form'
import { useLocation, useSearchParams } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { PhoneField } from '@/features/auth/components/PhoneField'
import { SocialButtons } from '@/entities/session/ui/SocialButtons'
import { useLogin } from '@/features/auth/hooks/useLogin'
import { fallbackMessageFor } from '@/shared/api/errorMessages'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { BackLink, Button, TextLink } from '@/shared/ui'

/** A-1. 로그인 — UX 설계서 §3.2 */
export function LoginPage() {
  const { form, submit, bannerMessage, canSubmit, isSubmitting } = useLogin()
  const { control, register, formState } = form
  const [searchParams] = useSearchParams()

  /**
   * 비밀번호 재설정을 마치고 넘어오면 그 사실을 **배너로** 알린다(UX §3.4).
   * 토스트는 4초 뒤 사라져 "왜 여기 왔는지"를 잃는다.
   */
  const notice = (useLocation().state as { banner?: string } | null)?.banner ?? null

  /**
   * 소셜 콜백은 302로 끝나므로 **서버 오류 봉투가 오지 않는다.** 코드만 쿼리로 오고
   * 화면이 한국어로 옮긴다(소셜 문서 §3). 사용자가 동의 화면에서 그만둔 경우에는
   * 코드가 아예 없으며, 그때는 아무 것도 띄우지 않는다 — 스스로 그만둔 것이다.
   */
  const socialError = searchParams.get('social_error')
  const socialMessage = socialError ? fallbackMessageFor(socialError) : null

  /** 로그인 후 돌아갈 곳. 소셜도 전화번호 로그인과 같은 목적지를 쓴다. */
  const next = searchParams.get('next') ?? paths.gallery

  return (
    <div className="gk-container-form flex min-h-screen flex-col justify-center py-12">
      <h1 className="mb-8 text-center text-title-md text-primary">{screenTitles.login}</h1>

      {notice && !bannerMessage && !socialMessage ? (
        <FormBanner tone="info" message={notice} className="mb-4" />
      ) : null}
      {socialMessage && !bannerMessage ? (
        <FormBanner message={socialMessage} className="mb-4" />
      ) : null}
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

        <Button type="submit" size="lg" block loading={isSubmitting} disabled={!canSubmit}>
          {actions.login}
        </Button>
      </form>

      <div className="mt-6 flex justify-center">
        <TextLink to={paths.passwordReset} tone="tertiary">
          {screens.login.forgotPassword}
        </TextLink>
      </div>

      <SocialButtons next={next} />

      <BackLink to={paths.landing} label={actions.backHome} />
    </div>
  )
}

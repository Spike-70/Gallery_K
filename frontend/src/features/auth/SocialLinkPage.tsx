import { Controller } from 'react-hook-form'

import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { PhoneField } from '@/features/auth/components/PhoneField'
import { TermsAgreement } from '@/features/auth/components/TermsAgreement'
import { useSocialLink } from '@/features/auth/hooks/useSocialLink'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { BackLink, Button, FieldGroup, TextButton, TextField } from '@/shared/ui'

/**
 * A-4. 계정 연결 — UX 설계서 §3.2-1, 소셜 문서 §5
 *
 * 소셜 인증은 끝났고 남은 것은 **이 사람이 어느 회원인지**뿐이다. 자동 가입하지
 * 않는 이유는 전화번호다 — 아침 알림·대행 가입·차단·회원 관리가 전부 전화번호에
 * 걸려 있어, 전화번호 없는 회원은 운영 화면에서 다룰 수 없다(SA-2).
 *
 * 연결 티켓은 HttpOnly 쿠키에 있다. 화면은 그것을 읽지 못하며, 만료는 서버가
 * `SOCIAL_LINK_EXPIRED`로 알려 준다 — 그때 훅이 A-1으로 돌려보낸다.
 */
export function SocialLinkPage() {
  const {
    mode,
    switchMode,
    linkForm,
    signupForm,
    submitLink,
    submitSignup,
    bannerMessage,
    suggestLinking,
    isSubmitting,
  } = useSocialLink()

  const isExisting = mode === 'existing'
  const form = isExisting ? linkForm : signupForm

  return (
    <div className="gk-container-form flex min-h-screen flex-col justify-center py-12">
      <h1 className="mb-2 text-center text-title-md text-primary">{screenTitles.socialLink}</h1>
      <p className="mb-8 text-center text-body-sm text-secondary">
        {isExisting ? screens.social.linkExistingGuide : screens.social.linkNewGuide}
      </p>

      {bannerMessage ? (
        <FormBanner
          message={bannerMessage}
          className="mb-4"
          action={
            suggestLinking ? (
              <TextButton tone="accent" onClick={() => switchMode('existing')}>
                {screens.social.toExisting}
              </TextButton>
            ) : undefined
          }
        />
      ) : null}

      <form
        onSubmit={isExisting ? submitLink : submitSignup}
        noValidate
        className="flex flex-col gap-5"
      >
        <Controller
          control={form.control as never}
          name="phone"
          render={({ field, fieldState }) => (
            <PhoneField
              label={screens.login.phoneLabel}
              value={field.value as string}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
              disabled={isSubmitting}
            />
          )}
        />

        {isExisting ? (
          <PasswordField
            label={screens.login.passwordLabel}
            autoComplete="current-password"
            error={linkForm.formState.errors.password?.message}
            disabled={isSubmitting}
            {...linkForm.register('password')}
          />
        ) : (
          <>
            <FieldGroup
              id="social-name"
              label={screens.signup.nameLabel}
              hint={screens.signup.nameHint}
              error={signupForm.formState.errors.name?.message}
              required
            >
              <TextField
                id="social-name"
                autoComplete="name"
                invalid={Boolean(signupForm.formState.errors.name)}
                disabled={isSubmitting}
                {...signupForm.register('name')}
              />
            </FieldGroup>

            <Controller
              control={signupForm.control}
              name="agreedTerms"
              render={({ field, fieldState }) => (
                <TermsAgreement
                  checked={Boolean(field.value)}
                  onChange={field.onChange}
                  error={fieldState.error?.message}
                />
              )}
            />
          </>
        )}

        <Button type="submit" size="lg" block loading={isSubmitting}>
          {isExisting ? screens.social.submitLink : screens.social.submitNew}
        </Button>
      </form>

      <div className="mt-6 flex justify-center">
        <TextButton
          tone="tertiary"
          onClick={() => switchMode(isExisting ? 'new' : 'existing')}
          disabled={isSubmitting}
        >
          {isExisting ? screens.social.toNew : screens.social.toExisting}
        </TextButton>
      </div>

      <BackLink to={paths.login} label={actions.backLogin} />
    </div>
  )
}

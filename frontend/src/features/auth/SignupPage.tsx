import { Controller } from 'react-hook-form'

import { paths } from '@/shared/config/paths'
import { FormBanner } from '@/features/auth/components/FormBanner'
import { PasswordField } from '@/features/auth/components/PasswordField'
import { PhoneField } from '@/features/auth/components/PhoneField'
import { TermsAgreement } from '@/features/auth/components/TermsAgreement'
import { useSignup } from '@/features/auth/hooks/useSignup'
import { PushPermissionPrompt } from '@/features/notification'
import { LIMITS } from '@/shared/config/constants'
import { actions, screenTitles, screens } from '@/shared/config/messages'
import { BackLink, Button, FieldGroup, Icon, TextField, TextLink } from '@/shared/ui'

/** D. 회원가입 — UX 설계서 §3.3. 필수 입력은 3개뿐이며 목표는 60초다. */
export function SignupPage() {
  const { form, submit, bannerMessage, passwordSatisfied, phoneTaken, closed, showNotifyPrompt, finishOnboarding, isSubmitting } =
    useSignup()
  const { control, register, formState } = form

  // 가입 잠금은 화면 전체를 대체한다(UX §3.3).
  if (closed) {
    return (
      <div className="gk-container-form flex min-h-screen flex-col justify-center gap-8 text-center">
        <p className="text-title-md text-primary">{screens.signup.closedTitle}</p>
        <BackLink to={paths.landing} label={actions.backHome} />
      </div>
    )
  }

  return (
    <div className="gk-container-form flex min-h-screen flex-col py-12">
      <h1 className="text-title-md text-primary">{screenTitles.signup}</h1>

      {/* 취지 본문 — PRD §6.4의 초안을 그대로 사용한다. */}
      <div className="mt-4 flex flex-col gap-1">
        {screens.signup.intro.map((line) => (
          <p key={line} className="text-body-md text-secondary">
            {line}
          </p>
        ))}
      </div>

      {bannerMessage ? <FormBanner message={bannerMessage} className="mt-6" /> : null}

      <form onSubmit={submit} noValidate className="mt-8 flex flex-col gap-5">
        <Controller
          control={control}
          name="phone"
          render={({ field, fieldState }) => (
            <PhoneField
              label={screens.signup.phoneLabel}
              hint={screens.signup.phoneHint}
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              error={fieldState.error?.message}
              disabled={isSubmitting}
            />
          )}
        />

        <PasswordField
          label={screens.signup.passwordLabel}
          hint={
            passwordSatisfied ? (
              <span className="flex items-center gap-1 text-accent">
                <Icon name="check" size="sm" className="h-4 w-4" />
                {screens.signup.passwordOk}
              </span>
            ) : (
              screens.signup.passwordHint
            )
          }
          autoComplete="new-password"
          error={formState.errors.password?.message}
          disabled={isSubmitting}
          {...register('password')}
        />

        <FieldGroup
          id="name"
          label={screens.signup.nameLabel}
          hint={screens.signup.nameHint}
          error={formState.errors.name?.message}
          required
        >
          <TextField
            id="name"
            autoComplete="name"
            maxLength={LIMITS.memberName}
            invalid={Boolean(formState.errors.name)}
            disabled={isSubmitting}
            {...register('name')}
          />
        </FieldGroup>

        <Controller
          control={control}
          name="agreedTerms"
          render={({ field, fieldState }) => (
            <TermsAgreement
              checked={field.value}
              onChange={(checked) => field.onChange(checked)}
              error={fieldState.error?.message}
            />
          )}
        />

        <Button type="submit" size="lg" block loading={isSubmitting}>
          {screens.signup.submit}
        </Button>
      </form>

      {/* `로그인하러 가기`는 **이미 가입된 번호일 때만** 나온다(UX §3.3 오류표). */}
      {phoneTaken ? (
        <div className="mt-6 flex justify-center">
          <TextLink to={paths.login}>{actions.goLogin}</TextLink>
        </div>
      ) : null}

      <BackLink to={paths.landing} label={actions.backHome} />

      {showNotifyPrompt ? <PushPermissionPrompt onDone={finishOnboarding} /> : null}
    </div>
  )
}

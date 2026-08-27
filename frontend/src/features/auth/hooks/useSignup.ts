import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { useSignupMutation } from '@/entities/session/api/queries'
import { hasAskedNotifyPermission } from '@/features/notification'
import { type SignupForm, signupSchema } from '@/features/auth/model/schemas'
import { LIMITS } from '@/shared/config/constants'
import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { applyApiError } from '@/shared/lib/formErrors'
import { normalizePhone } from '@/shared/lib/phone'

/**
 * D 회원가입 — UX 설계서 §3.3
 *
 * 흐름: 제출 → 가입 + 자동 로그인 → **알림 권한 안내** → C 갤러리.
 * 가입 잠금(`SIGNUP_CLOSED`)은 필드 오류가 아니라 화면 대체다.
 */
export function useSignup() {
  const navigate = useNavigate()
  const mutation = useSignupMutation()
  const [bannerMessage, setBannerMessage] = useState<string | null>(null)
  const [closed, setClosed] = useState(false)
  const [phoneTaken, setPhoneTaken] = useState(false)
  const [showNotifyPrompt, setShowNotifyPrompt] = useState(false)

  const form = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    mode: 'onBlur',
    defaultValues: { phone: '', password: '', name: '', agreedTerms: false as true },
  })

  /**
   * UX §3.3 — 비밀번호 힌트는 **실시간**으로 바뀐다. 흐릿한 규칙을 외우게 하지 않고
   * 지금 충족했는지를 그 자리에서 보여준다. 검증(제출 차단)은 여전히 스키마가 한다.
   */
  const passwordSatisfied = form.watch('password').length >= LIMITS.passwordMin

  const submit = form.handleSubmit(async (values) => {
    setBannerMessage(null)
    setPhoneTaken(false)
    try {
      await mutation.mutateAsync({
        phone: normalizePhone(values.phone),
        password: values.password,
        name: values.name,
        agreedTerms: values.agreedTerms,
      })
      // 이미 `나중에`를 누른 적이 있으면 다시 묻지 않는다(UX §3.3). 설정에서 언제든 켤 수 있다.
      if (hasAskedNotifyPermission()) navigate(paths.gallery, { replace: true })
      else setShowNotifyPrompt(true)
    } catch (error) {
      if (isApiError(error) && error.code === ERROR_CODES.signupClosed) {
        setClosed(true)
        return
      }
      if (isApiError(error) && error.code === ERROR_CODES.signupPhoneTaken) {
        form.setError('phone', { type: 'server', message: error.message })
        setPhoneTaken(true)
        return
      }
      setBannerMessage(applyApiError(error, form.setError))
    }
  })

  const finishOnboarding = () => {
    setShowNotifyPrompt(false)
    navigate(paths.gallery, { replace: true })
  }

  return {
    form,
    submit,
    bannerMessage,
    passwordSatisfied,
    /** `이미 가입된 번호입니다.` — 이때만 `로그인하러 가기`를 함께 보여준다(UX §3.3) */
    phoneTaken,
    closed,
    showNotifyPrompt,
    finishOnboarding,
    isSubmitting: mutation.isPending,
  }
}

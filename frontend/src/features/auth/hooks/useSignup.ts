import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { useSignupMutation } from '@/entities/session/api/queries'
import { type SignupForm, signupSchema } from '@/features/auth/model/schemas'
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
  const [showNotifyPrompt, setShowNotifyPrompt] = useState(false)

  const form = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    mode: 'onBlur',
    defaultValues: { phone: '', password: '', name: '', agreedTerms: false as true },
  })

  const submit = form.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      await mutation.mutateAsync({
        phone: normalizePhone(values.phone),
        password: values.password,
        name: values.name,
        agreedTerms: values.agreedTerms,
      })
      setShowNotifyPrompt(true)
    } catch (error) {
      if (isApiError(error) && error.code === ERROR_CODES.signupClosed) {
        setClosed(true)
        return
      }
      if (isApiError(error) && error.code === ERROR_CODES.signupPhoneTaken) {
        form.setError('phone', { type: 'server', message: error.message })
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
    closed,
    showNotifyPrompt,
    finishOnboarding,
    isSubmitting: mutation.isPending,
  }
}

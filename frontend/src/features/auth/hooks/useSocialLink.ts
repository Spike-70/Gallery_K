import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'

import { useSocialLinkMutation, useSocialSignupMutation } from '@/entities/session/api/queries'
import {
  type SocialLinkForm,
  type SocialSignupForm,
  socialLinkSchema,
  socialSignupSchema,
} from '@/features/auth/model/schemas'
import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { applyApiError } from '@/shared/lib/formErrors'
import { normalizePhone } from '@/shared/lib/phone'

/**
 * A-4 계정 연결 — UX 설계서 §3.2-1, 소셜 문서 §5
 *
 * 모드를 **사용자가 고른다.** 전화번호를 넣었을 때 서버가 "이미 가입된 번호입니다"를
 * 먼저 알려주면 그 자체로 회원 명단 조회 수단이 된다(SA-5).
 *
 * 전화번호 입력값은 모드를 바꿔도 유지한다 — 다시 치게 하지 않는다.
 */
export type LinkMode = 'existing' | 'new'

export function useSocialLink() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<LinkMode>('existing')
  const [bannerMessage, setBannerMessage] = useState<string | null>(null)
  /** 신규 모드에서 이미 가입된 번호였다면 연결 모드로 가는 길을 열어 준다 */
  const [suggestLinking, setSuggestLinking] = useState(false)

  const linkMutation = useSocialLinkMutation()
  const signupMutation = useSocialSignupMutation()

  const linkForm = useForm<SocialLinkForm>({
    resolver: zodResolver(socialLinkSchema),
    mode: 'onBlur',
    defaultValues: { phone: '', password: '' },
  })
  const signupForm = useForm<SocialSignupForm>({
    resolver: zodResolver(socialSignupSchema),
    mode: 'onBlur',
    defaultValues: { phone: '', name: '', agreedTerms: false as unknown as true },
  })

  /** 티켓이 만료되면 A-1으로 돌려보낸다. 이 화면에 머물러 봐야 할 수 있는 일이 없다. */
  const handleFailure = (error: unknown, setError: (message: string | null) => void) => {
    if (isApiError(error) && error.code === ERROR_CODES.socialLinkExpired) {
      navigate(paths.login, { replace: true, state: { banner: screens.social.expired } })
      return
    }
    if (isApiError(error) && error.code === ERROR_CODES.signupPhoneTaken) {
      setSuggestLinking(true)
    }
    setError(null)
  }

  const switchMode = (next: LinkMode) => {
    // 입력한 번호를 옮겨 준다. 모드를 바꿨다고 처음부터 다시 치게 하지 않는다.
    const phone = mode === 'existing' ? linkForm.getValues('phone') : signupForm.getValues('phone')
    if (next === 'existing') linkForm.setValue('phone', phone)
    else signupForm.setValue('phone', phone)
    setBannerMessage(null)
    setSuggestLinking(false)
    setMode(next)
  }

  const submitLink = linkForm.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      await linkMutation.mutateAsync({
        phone: normalizePhone(values.phone),
        password: values.password,
      })
      navigate(paths.gallery, { replace: true })
    } catch (error) {
      handleFailure(error, () => setBannerMessage(applyApiError(error, linkForm.setError)))
    }
  })

  const submitSignup = signupForm.handleSubmit(async (values) => {
    setBannerMessage(null)
    setSuggestLinking(false)
    try {
      await signupMutation.mutateAsync({
        phone: normalizePhone(values.phone),
        name: values.name,
        agreedTerms: true,
      })
      navigate(paths.gallery, { replace: true })
    } catch (error) {
      handleFailure(error, () => setBannerMessage(applyApiError(error, signupForm.setError)))
    }
  })

  return {
    mode,
    switchMode,
    linkForm,
    signupForm,
    submitLink,
    submitSignup,
    bannerMessage,
    suggestLinking,
    isSubmitting: linkMutation.isPending || signupMutation.isPending,
  }
}

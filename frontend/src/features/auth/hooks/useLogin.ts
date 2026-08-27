import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { useLoginMutation } from '@/entities/session/api/queries'
import { type LoginForm, loginSchema } from '@/features/auth/model/schemas'
import { applyApiError } from '@/shared/lib/formErrors'
import { normalizePhone } from '@/shared/lib/phone'

/**
 * A-1 로그인 — UX 설계서 §3.2
 *
 * 성공하면 **C 갤러리로 직행한다.** 첫 화면으로 되돌리지 않는다.
 * `next` 파라미터가 있으면 원래 가려던 곳으로 보낸다(`RequireAuth`가 붙인다).
 * 자동 로그인 체크박스는 없다 — 90일 세션이 기본 동작이다(GAP-14).
 */
export function useLogin() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const mutation = useLoginMutation()
  const [bannerMessage, setBannerMessage] = useState<string | null>(null)

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    defaultValues: { phone: '', password: '' },
  })

  // UX §3.2 — 두 필드가 채워지기 전에는 버튼을 활성화하지 않는다.
  const [phone, password] = form.watch(['phone', 'password'])
  const canSubmit = phone.trim().length > 0 && password.length > 0

  const submit = form.handleSubmit(async (values) => {
    setBannerMessage(null)
    try {
      const user = await mutation.mutateAsync({
        phone: normalizePhone(values.phone),
        password: values.password,
      })

      // 초기 비밀번호 계정은 곧바로 변경 화면으로 보낸다(UX §3.5).
      if (user.mustChangePassword) {
        navigate(paths.passwordChange, { replace: true })
        return
      }

      const next = searchParams.get('next')
      navigate(next ?? paths.gallery, { replace: true })
    } catch (error) {
      setBannerMessage(applyApiError(error, form.setError))
    }
  })

  return { form, submit, bannerMessage, canSubmit, isSubmitting: mutation.isPending }
}

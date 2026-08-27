import { z } from 'zod'

import { LIMITS } from '@/shared/config/constants'
import { validation } from '@/shared/config/messages'
import { normalizePhone } from '@/shared/lib/phone'

/**
 * 폼 스키마 — 프런트엔드 아키텍처 문서 §2
 *
 * 클라이언트 검증은 **서버 검증의 축소판이 아니라 즉시 피드백 수단**이다.
 * 최종 판정은 서버가 하며, `field_errors`가 오면 그대로 필드에 주입한다(§7.2).
 */

const phoneField = z
  .string()
  .min(1, validation.phoneRequired)
  .refine((value) => /^01[0-9]{8,9}$/.test(normalizePhone(value)), validation.phoneFormat)

const passwordField = z
  .string()
  .min(LIMITS.passwordMin, validation.passwordTooShort)
  .max(LIMITS.passwordMax, validation.passwordTooLong)

export const loginSchema = z.object({
  phone: phoneField,
  // 로그인은 길이 정책을 검사하지 않는다. 기존 비밀번호를 우리가 판단할 이유가 없다.
  password: z.string().min(1, validation.passwordRequired),
})
export type LoginForm = z.infer<typeof loginSchema>

export const signupSchema = z.object({
  phone: phoneField,
  password: passwordField,
  name: z.string().min(1, validation.nameRequired).max(LIMITS.memberName, validation.nameTooLong),
  agreedTerms: z.literal(true, { message: validation.termsRequired }),
})
export type SignupForm = z.infer<typeof signupSchema>

export const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, validation.passwordRequired),
  newPassword: passwordField,
})
export type PasswordChangeForm = z.infer<typeof passwordChangeSchema>

export const passwordResetRequestSchema = z.object({ phone: phoneField })
export type PasswordResetRequestForm = z.infer<typeof passwordResetRequestSchema>

export const passwordResetConfirmSchema = z.object({
  code: z.string().regex(/^\d{6}$/, validation.codeFormat),
  newPassword: passwordField,
})
export type PasswordResetConfirmForm = z.infer<typeof passwordResetConfirmSchema>

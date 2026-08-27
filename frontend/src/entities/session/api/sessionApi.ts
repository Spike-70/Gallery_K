import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawSession, RawSessionUser } from '@/shared/api/types'

import { toSession, toSessionUser } from '@/entities/session/api/mappers'
import type { Session, SessionUser } from '@/entities/session/model/types'

/**
 * 세션·계정 API — API 명세서 §6·§8
 *
 * 세션 토큰은 HttpOnly 쿠키로만 오간다. 이 모듈은 토큰을 보지도 저장하지도 않는다(§12).
 */

/** `GET /auth/session` — 앱 부팅 시 1회. 비로그인이어도 200이다. */
export async function fetchSession(): Promise<Session> {
  const raw = await httpClient.get<RawSession>(endpoints.auth.session())
  return toSession(raw)
}

/** `POST /auth/login` */
export async function login(input: { phone: string; password: string }): Promise<SessionUser> {
  const raw = await httpClient.post<{ user: RawSessionUser }>(endpoints.auth.login(), {
    phone: input.phone,
    password: input.password,
  })
  return toSessionUser(raw.user)
}

/** `POST /auth/signup` — 성공 시 자동 로그인 상태가 된다 */
export async function signup(input: {
  phone: string
  password: string
  name: string
  agreedTerms: boolean
}): Promise<SessionUser> {
  const raw = await httpClient.post<{ user: RawSessionUser; is_first_login: boolean }>(
    endpoints.auth.signup(),
    {
      phone: input.phone,
      password: input.password,
      name: input.name,
      agreed_terms: input.agreedTerms,
    },
  )
  return toSessionUser(raw.user)
}

/** `POST /auth/logout` */
export async function logout(): Promise<void> {
  await httpClient.post(endpoints.auth.logout())
}

/** `POST /auth/password` — 다른 단말 세션은 모두 만료된다 */
export async function changePassword(input: {
  currentPassword: string
  newPassword: string
}): Promise<SessionUser> {
  const raw = await httpClient.post<{ user: RawSessionUser }>(endpoints.auth.password(), {
    current_password: input.currentPassword,
    new_password: input.newPassword,
  })
  return toSessionUser(raw.user)
}

/** `POST /auth/password/reset/request` *(v1.1)* — 미가입 번호에도 성공 응답을 준다 */
export async function requestPasswordReset(input: { phone: string }): Promise<{
  expiresInSeconds: number
  resendAfterSeconds: number
}> {
  const raw = await httpClient.post<{ expires_in_seconds: number; resend_after_seconds: number }>(
    endpoints.auth.passwordResetRequest(),
    { phone: input.phone },
  )
  return { expiresInSeconds: raw.expires_in_seconds, resendAfterSeconds: raw.resend_after_seconds }
}

/** `POST /auth/password/reset/confirm` *(v1.1)* — 자동 로그인하지 않는다 */
export async function confirmPasswordReset(input: {
  phone: string
  code: string
  newPassword: string
}): Promise<void> {
  await httpClient.post(endpoints.auth.passwordResetConfirm(), {
    phone: input.phone,
    code: input.code,
    new_password: input.newPassword,
  })
}

/** `GET /me` */
export async function fetchMe(): Promise<SessionUser> {
  const raw = await httpClient.get<{ user: RawSessionUser }>(endpoints.me.root())
  return toSessionUser(raw.user)
}

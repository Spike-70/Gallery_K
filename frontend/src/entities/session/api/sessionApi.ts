import type { RawSession, RawSessionUser } from '@/shared/api/types'
// [API] 백엔드 연동 시 아래 두 줄의 주석을 해제한다.
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'

import { toSession, toSessionUser } from '@/entities/session/api/mappers'
import type { Session, SessionUser } from '@/entities/session/model/types'

// [MOCK] 데모 전용 — `src/mocks/README.md`의 3단계로 제거한다.
import * as authMock from '@/mocks/handlers/authHandlers'
import * as meMock from '@/mocks/handlers/meHandlers'

/**
 * 세션·계정 API — API 명세서 §6·§8
 *
 * 각 함수는 **실제 호출(`[API]`)과 데모 목(`[MOCK]`)이 나란히** 있으며 반환 타입이 같다.
 * 교체는 주석을 옮기는 것으로 끝난다. `grep -rn "\[MOCK\]" src/`로 전수를 찾을 수 있다.
 */

/** `GET /auth/session` — 앱 부팅 시 1회 */
export async function fetchSession(): Promise<Session> {
  // [API]
  // const raw = await httpClient.get<RawSession>(endpoints.auth.session())
  // return toSession(raw)

  // [MOCK]
  const raw: RawSession = await authMock.getSession()
  return toSession(raw)
}

/** `POST /auth/login` */
export async function login(input: { phone: string; password: string }): Promise<SessionUser> {
  // [API]
  // const raw = await httpClient.post<{ user: RawSessionUser }>(endpoints.auth.login(), {
  //   phone: input.phone,
  //   password: input.password,
  // })
  // return toSessionUser(raw.user)

  // [MOCK]
  const raw = await authMock.login(input)
  return toSessionUser(raw.user)
}

/** `POST /auth/signup` — 성공 시 자동 로그인 상태가 된다 */
export async function signup(input: {
  phone: string
  password: string
  name: string
  agreedTerms: boolean
}): Promise<SessionUser> {
  // [API]
  // const raw = await httpClient.post<{ user: RawSessionUser; is_first_login: boolean }>(
  //   endpoints.auth.signup(),
  //   { phone: input.phone, password: input.password, name: input.name, agreed_terms: input.agreedTerms },
  // )
  // return toSessionUser(raw.user)

  // [MOCK]
  const raw = await authMock.signup(input)
  return toSessionUser(raw.user)
}

/** `POST /auth/logout` */
export async function logout(): Promise<void> {
  // [API]
  // await httpClient.post(endpoints.auth.logout())

  // [MOCK]
  await authMock.logout()
}

/** `POST /auth/password` — 다른 단말 세션은 모두 만료된다 */
export async function changePassword(input: {
  currentPassword: string
  newPassword: string
}): Promise<SessionUser> {
  // [API]
  // const raw = await httpClient.post<{ user: RawSessionUser }>(endpoints.auth.password(), {
  //   current_password: input.currentPassword,
  //   new_password: input.newPassword,
  // })
  // return toSessionUser(raw.user)

  // [MOCK]
  const raw = await authMock.changePassword(input)
  return toSessionUser(raw.user)
}

/** `POST /auth/password/reset/request` *(v1.1)* — 미가입 번호에도 성공 응답을 준다 */
export async function requestPasswordReset(input: { phone: string }): Promise<{
  expiresInSeconds: number
  resendAfterSeconds: number
}> {
  // [API]
  // const raw = await httpClient.post<{ expires_in_seconds: number; resend_after_seconds: number }>(
  //   endpoints.auth.passwordResetRequest(),
  //   { phone: input.phone },
  // )
  // return { expiresInSeconds: raw.expires_in_seconds, resendAfterSeconds: raw.resend_after_seconds }

  // [MOCK]
  void input
  const raw = await authMock.requestPasswordReset()
  return { expiresInSeconds: raw.expires_in_seconds, resendAfterSeconds: raw.resend_after_seconds }
}

/** `POST /auth/password/reset/confirm` *(v1.1)* — 자동 로그인하지 않는다 */
export async function confirmPasswordReset(input: {
  phone: string
  code: string
  newPassword: string
}): Promise<void> {
  // [API]
  // await httpClient.post(endpoints.auth.passwordResetConfirm(), {
  //   phone: input.phone,
  //   code: input.code,
  //   new_password: input.newPassword,
  // })

  // [MOCK]
  await authMock.confirmPasswordReset(input)
}

/** `GET /me` */
export async function fetchMe(): Promise<SessionUser> {
  // [API]
  // const raw = await httpClient.get<{ user: RawSessionUser }>(endpoints.me.root())
  // return toSessionUser(raw.user)

  // [MOCK]
  const raw = await meMock.getMe()
  return toSessionUser(raw.user)
}

/** `POST /media/session` — 만료 10분 전에 호출한다(프런트 §8.2) */
export async function refreshMediaSession(): Promise<{ expiresAt: string }> {
  // [API]
  // const raw = await httpClient.post<{ expires_at: string; resource_prefix: string }>(
  //   endpoints.media.session(),
  // )
  // return { expiresAt: raw.expires_at }

  // [MOCK]
  const raw = await authMock.createMediaSession()
  return { expiresAt: raw.expires_at }
}

// 실제 호출로 교체할 때 타입이 즉시 맞도록 원형 타입을 여기서 참조해 둔다.
export type { RawSession, RawSessionUser }

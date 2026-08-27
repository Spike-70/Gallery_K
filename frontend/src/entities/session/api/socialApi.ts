import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawSessionUser, RawSocialIdentity, RawSocialProvider } from '@/shared/api/types'
import type { Uuid } from '@/shared/types/utility'

import {
  toSessionUser,
  toSocialIdentity,
  toSocialProviderOption,
} from '@/entities/session/api/mappers'
import type {
  SessionUser,
  SocialIdentity,
  SocialProviderOption,
} from '@/entities/session/model/types'

/**
 * 소셜 로그인 API — API 명세서 §6.11–§6.15·§8.7–§8.8
 *
 * **인가 왕복(`start`·`callback`)은 여기에 없다.** 그 둘은 브라우저가 직접 이동하는
 * 경로이며 `<a href>`의 목적지다(소셜 문서 SA-1). `fetch`로 부르면 302를 따라가
 * 제공자 HTML을 받아 오게 되고, 리다이렉트 방식 자체가 성립하지 않는다.
 */

/** `GET /auth/social/providers` — 켜진 제공자만 온다 */
export async function fetchSocialProviders(): Promise<SocialProviderOption[]> {
  const raw = await httpClient.get<{ providers: RawSocialProvider[] }>(
    endpoints.auth.socialProviders(),
  )
  return raw.providers.map(toSocialProviderOption)
}

/** `POST /auth/social/link` — 기존 계정에 연결. 비밀번호로 소유를 증명한다 */
export async function linkSocialAccount(input: {
  phone: string
  password: string
}): Promise<SessionUser> {
  const raw = await httpClient.post<{ user: RawSessionUser }>(endpoints.auth.socialLink(), {
    phone: input.phone,
    password: input.password,
  })
  return toSessionUser(raw.user)
}

/** `POST /auth/social/signup` — 소셜 신규 가입. 비밀번호를 만들지 않는다 */
export async function signupWithSocial(input: {
  phone: string
  name: string
  agreedTerms: boolean
}): Promise<SessionUser> {
  const raw = await httpClient.post<{ user: RawSessionUser; is_first_login: boolean }>(
    endpoints.auth.socialSignup(),
    { phone: input.phone, name: input.name, agreed_terms: input.agreedTerms },
  )
  return toSessionUser(raw.user)
}

export type SocialIdentityList = {
  identities: SocialIdentity[]
  /** false면 화면이 해제 버튼을 잠근다. 마지막 로그인 수단이기 때문이다 */
  canUnlink: boolean
}

/** `GET /me/social-identities` */
export async function fetchSocialIdentities(): Promise<SocialIdentityList> {
  const raw = await httpClient.get<{ identities: RawSocialIdentity[]; can_unlink: boolean }>(
    endpoints.me.socialIdentities(),
  )
  return { identities: raw.identities.map(toSocialIdentity), canUnlink: raw.can_unlink }
}

/** `DELETE /me/social-identities/{id}` */
export async function unlinkSocialIdentity(id: Uuid): Promise<void> {
  await httpClient.delete(endpoints.me.socialIdentity(id))
}

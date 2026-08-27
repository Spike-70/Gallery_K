import { ERROR_CODES } from '@/shared/api/ApiError'
import type { RawSession, RawSessionUser } from '@/shared/api/types'
import { LIMITS } from '@/shared/config/constants'
import { normalizePhone } from '@/shared/lib/phone'

import { type MockMember, db, getSetting, nowIso, uuid } from '@/mocks/db'
import { mockDelay, mockFail } from '@/mocks/lib/mockClient'
import { mustChangePassword, requireMember, toSessionUser } from '@/mocks/lib/serializers'

/**
 * 인증 핸들러 — API 명세서 §6.3~§6.10
 *
 * 계정 존재 여부를 노출하지 않는다(PRD §6.2). 미가입·비밀번호 불일치·차단 회원은
 * 모두 `AUTH_INVALID_CREDENTIALS`로 동일하게 응답한다.
 */

const MEDIA_SESSION_HOURS = 6

function issueMediaSession(): string {
  const expires = new Date(Date.now() + MEDIA_SESSION_HOURS * 3600_000).toISOString()
  db.mediaSessionExpiresAt = expires
  return expires
}

function findByPhone(phone: string): MockMember | undefined {
  const normalized = normalizePhone(phone)
  return db.members.find((member) => member.phone === normalized)
}

/** `POST /auth/login` */
export async function login(input: { phone: string; password: string }): Promise<{ user: RawSessionUser }> {
  await mockDelay(null, 420)
  const member = findByPhone(input.phone)
  if (!member || member.password !== input.password || member.is_blocked) {
    mockFail(ERROR_CODES.authInvalidCredentials, 401)
  }
  db.currentUserId = member.id
  issueMediaSession()
  return { user: toSessionUser(member) }
}

/** `POST /auth/signup` — 가입 성공 시 자동 로그인된다(PRD §6.4) */
export async function signup(input: {
  phone: string
  password: string
  name: string
  agreedTerms: boolean
}): Promise<{ user: RawSessionUser; is_first_login: true }> {
  await mockDelay(null, 500)

  if (!getSetting('signup_open', true)) {
    mockFail(ERROR_CODES.signupClosed, 403)
  }
  if (findByPhone(input.phone)) {
    mockFail(ERROR_CODES.signupPhoneTaken, 409)
  }
  if (input.password.length < LIMITS.passwordMin) {
    mockFail(ERROR_CODES.passwordPolicyViolation, 422)
  }

  const member: MockMember = {
    id: uuid(`mbnew${db.members.length}`, db.members.length),
    name: input.name,
    phone: normalizePhone(input.phone),
    role: 'viewer',
    created_at: nowIso(),
    created_via: 'self',
    is_blocked: false,
    blocked_at: null,
    notify_enabled: false,
    notify_at: getSetting('notify_default_hour', '07:30'),
    push_status: 'none',
    push_platforms: [],
    last_login_at: nowIso(),
    last_viewed_on: null,
    password: input.password,
  }
  db.members.push(member)
  db.currentUserId = member.id
  issueMediaSession()

  return { user: toSessionUser(member), is_first_login: true }
}

/** `POST /auth/logout` */
export async function logout(): Promise<Record<string, never>> {
  await mockDelay(null, 160)
  db.currentUserId = null
  db.mediaSessionExpiresAt = null
  return {}
}

/** `GET /auth/session` — 비로그인이어도 200이다 */
export function getSession(): Promise<RawSession> {
  const member = db.members.find((candidate) => candidate.id === db.currentUserId)
  return mockDelay(
    {
      is_authenticated: Boolean(member),
      user: member ? toSessionUser(member) : null,
      media_session_expires_at: member ? (db.mediaSessionExpiresAt ?? issueMediaSession()) : null,
    },
    180,
  )
}

/** `POST /auth/password` — 다른 단말 세션은 모두 만료된다 */
export async function changePassword(input: {
  currentPassword: string
  newPassword: string
}): Promise<{ user: RawSessionUser }> {
  await mockDelay(null, 420)
  const member = requireMember()
  if (member.password !== input.currentPassword) {
    mockFail(ERROR_CODES.passwordCurrentMismatch, 401)
  }
  if (input.newPassword.length < LIMITS.passwordMin) {
    mockFail(ERROR_CODES.passwordPolicyViolation, 422)
  }
  member.password = input.newPassword
  mustChangePassword.delete(member.id)
  return { user: toSessionUser(member) }
}

/** `POST /auth/password/reset/request` — 미가입 번호에도 동일한 성공 응답을 준다 */
export function requestPasswordReset(): Promise<{ expires_in_seconds: number; resend_after_seconds: number }> {
  return mockDelay({ expires_in_seconds: 180, resend_after_seconds: 60 }, 520)
}

/** `POST /auth/password/reset/confirm` — 자동 로그인하지 않는다 */
export async function confirmPasswordReset(input: {
  phone: string
  code: string
  newPassword: string
}): Promise<Record<string, never>> {
  await mockDelay(null, 460)
  // 데모 인증번호는 6자리 `000000`이다.
  if (input.code !== '000000') {
    mockFail(ERROR_CODES.resetCodeInvalid, 422, { details: { attempts_left: 4 } })
  }
  const member = findByPhone(input.phone)
  if (member) member.password = input.newPassword
  return {}
}

/** `POST /media/session` — CloudFront 서명 쿠키 발급 */
export function createMediaSession(): Promise<{ expires_at: string; resource_prefix: string }> {
  requireMember()
  return mockDelay({ expires_at: issueMediaSession(), resource_prefix: '/media/artworks/' }, 140)
}

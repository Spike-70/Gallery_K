import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import { type NumberedPage, toNumberedPage } from '@/shared/api/pagination'
import type { RawMemberItem } from '@/shared/api/types'
import { MEMBER_PAGE_SIZE } from '@/shared/config/constants'
import { normalizePhone } from '@/shared/lib/phone'
import type { Uuid } from '@/shared/types/utility'

import type { MemberListParams } from '@/entities/member/api/keys'
import { toMember } from '@/entities/member/api/mappers'
import type { Member } from '@/entities/member/model/types'

export type MemberListResult = NumberedPage<Member> & { signupOpen: boolean }

/** `GET /admin/members` — B-3. `signup_open`을 목록과 함께 받는다(API 문서 §9.13) */
export async function fetchMembers(params: MemberListParams): Promise<MemberListResult> {
  const { data, meta } = await httpClient.requestWithMeta<{
    members: RawMemberItem[]
    signup_open: boolean
  }>(endpoints.admin.members(), {
    query: {
      query: params.query,
      status: params.status,
      notify: params.notify,
      sort: params.sort,
      page: params.page,
      limit: MEMBER_PAGE_SIZE,
    },
  })
  return {
    ...toNumberedPage(data.members.map(toMember), meta.pagination),
    signupOpen: data.signup_open,
  }
}

/** `POST /admin/members` — 대행 가입. 가입 잠금 상태에서도 만들 수 있다 */
export async function createMember(input: {
  phone: string
  name: string
  initialPassword: string
}): Promise<Member> {
  const raw = await httpClient.post<{ member: RawMemberItem }>(endpoints.admin.members(), {
    phone: normalizePhone(input.phone),
    name: input.name,
    initial_password: input.initialPassword,
  })
  return toMember(raw.member)
}

/** `POST /admin/members/{id}/block` · `/unblock` — 멱등하다 */
export async function setMemberBlocked(id: Uuid, blocked: boolean): Promise<Member> {
  const raw = await httpClient.post<{ member: RawMemberItem }>(
    blocked ? endpoints.admin.memberBlock(id) : endpoints.admin.memberUnblock(id),
    // `unblock`은 바디를 받지 않는다. 빈 객체를 보내면 스키마가 없어 거부된다.
    blocked ? { reason: null } : undefined,
  )
  return toMember(raw.member)
}

/** `POST /admin/members/{id}/reset-password` — 회원의 모든 세션이 무효화된다 */
export async function resetMemberPassword(id: Uuid, newPassword: string): Promise<Member> {
  const raw = await httpClient.post<{ member: RawMemberItem }>(
    endpoints.admin.memberResetPassword(id),
    { new_password: newPassword },
  )
  return toMember(raw.member)
}

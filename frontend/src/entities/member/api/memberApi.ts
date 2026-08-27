import type { NumberedPage } from '@/shared/api/pagination'
// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import { toNumberedPage } from '@/shared/api/pagination'
// import type { RawMemberItem } from '@/shared/api/types'
import { MEMBER_PAGE_SIZE } from '@/shared/config/constants'
import { normalizePhone } from '@/shared/lib/phone'
import type { Uuid } from '@/shared/types/utility'

import type { MemberListParams } from '@/entities/member/api/keys'
import { toMember } from '@/entities/member/api/mappers'
import type { Member } from '@/entities/member/model/types'

// [MOCK]
import * as adminMock from '@/mocks/handlers/adminHandlers'

export type MemberListResult = NumberedPage<Member> & { signupOpen: boolean }

/** `GET /admin/members` — B-3. `signup_open`을 목록과 함께 받는다(API 문서 §9.13) */
export async function fetchMembers(params: MemberListParams): Promise<MemberListResult> {
  // [API]
  // const { data, meta } = await httpClient.requestWithMeta<{
  //   members: RawMemberItem[]
  //   signup_open: boolean
  // }>(endpoints.admin.members(), {
  //   query: {
  //     query: params.query,
  //     status: params.status,
  //     notify: params.notify,
  //     sort: params.sort,
  //     page: params.page,
  //     limit: MEMBER_PAGE_SIZE,
  //   },
  // })
  // return { ...toNumberedPage(data.members.map(toMember), meta.pagination), signupOpen: data.signup_open }

  // [MOCK]
  const result = await adminMock.getMembers({ ...params, limit: MEMBER_PAGE_SIZE })
  return {
    items: result.data.members.map(toMember),
    page: result.pagination.page ?? 1,
    totalCount: result.pagination.total_count ?? 0,
    totalPages: result.pagination.total_pages ?? 1,
    hasMore: result.pagination.has_more,
    signupOpen: result.data.signup_open,
  }
}

/** `POST /admin/members` — 대행 가입. 가입 잠금 상태에서도 만들 수 있다 */
export async function createMember(input: {
  phone: string
  name: string
  initialPassword: string
}): Promise<Member> {
  const phone = normalizePhone(input.phone)

  // [API]
  // const raw = await httpClient.post<{ member: RawMemberItem }>(endpoints.admin.members(), {
  //   phone,
  //   name: input.name,
  //   initial_password: input.initialPassword,
  // })
  // return toMember(raw.member)

  // [MOCK]
  const raw = await adminMock.createMember({ ...input, phone })
  return toMember(raw.member)
}

/** `POST /admin/members/{id}/block` · `/unblock` — 멱등하다 */
export async function setMemberBlocked(id: Uuid, blocked: boolean): Promise<Member> {
  // [API]
  // const raw = await httpClient.post<{ member: RawMemberItem }>(
  //   blocked ? endpoints.admin.memberBlock(id) : endpoints.admin.memberUnblock(id),
  //   blocked ? { reason: null } : undefined,
  // )
  // return toMember(raw.member)

  // [MOCK]
  const raw = await adminMock.setMemberBlocked(id, blocked)
  return toMember(raw.member)
}

/** `POST /admin/members/{id}/reset-password` — 회원의 모든 세션이 무효화된다 */
export async function resetMemberPassword(id: Uuid, newPassword: string): Promise<Member> {
  // [API]
  // const raw = await httpClient.post<{ member: RawMemberItem }>(endpoints.admin.memberResetPassword(id), {
  //   new_password: newPassword,
  // })
  // return toMember(raw.member)

  // [MOCK]
  const raw = await adminMock.resetMemberPassword(id, newPassword)
  return toMember(raw.member)
}

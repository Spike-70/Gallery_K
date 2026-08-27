import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { type MemberListParams, memberKeys } from '@/entities/member/api/keys'
import * as memberApi from '@/entities/member/api/memberApi'
import { CACHE_POLICY } from '@/shared/api/queryClient'

export function useMembersQuery(params: MemberListParams) {
  return useQuery({
    queryKey: memberKeys.list(params),
    queryFn: () => memberApi.fetchMembers(params),
    ...CACHE_POLICY.admin,
  })
}

function useInvalidateMembers() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: memberKeys.all })
}

export function useCreateMemberMutation() {
  const invalidate = useInvalidateMembers()
  return useMutation({ mutationFn: memberApi.createMember, onSuccess: () => void invalidate() })
}

/** 되돌리기 어려운 조작이므로 **낙관적 반영을 하지 않는다**(프런트 §6.4) */
export function useSetMemberBlockedMutation() {
  const invalidate = useInvalidateMembers()
  return useMutation({
    mutationFn: ({ id, blocked }: { id: string; blocked: boolean }) =>
      memberApi.setMemberBlocked(id, blocked),
    onSuccess: () => void invalidate(),
  })
}

export function useResetMemberPasswordMutation() {
  const invalidate = useInvalidateMembers()
  return useMutation({
    mutationFn: ({ id, newPassword }: { id: string; newPassword: string }) =>
      memberApi.resetMemberPassword(id, newPassword),
    onSuccess: () => void invalidate(),
  })
}

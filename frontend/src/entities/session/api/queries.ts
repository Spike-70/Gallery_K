import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { sessionKeys } from '@/entities/session/api/keys'
import * as sessionApi from '@/entities/session/api/sessionApi'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { resetSessionLostGuard } from '@/shared/api/httpClient'

/** `GET /auth/session` — 부팅 시퀀스의 1단계(프런트 §8.2) */
export function useSessionQuery() {
  return useQuery({
    queryKey: sessionKeys.session(),
    queryFn: sessionApi.fetchSession,
    ...CACHE_POLICY.me,
    retry: 1,
  })
}

export function useMeQuery(enabled = true) {
  return useQuery({
    queryKey: sessionKeys.me(),
    queryFn: sessionApi.fetchMe,
    enabled,
    ...CACHE_POLICY.me,
    refetchOnWindowFocus: true,
  })
}

/** 로그인·가입 성공 후 공통 처리: 스토어 반영 + 세션 캐시 무효화 */
function useSessionSuccess() {
  const queryClient = useQueryClient()
  const setAuthenticated = useSessionStore((state) => state.setAuthenticated)

  return (user: Parameters<typeof setAuthenticated>[0]) => {
    resetSessionLostGuard()
    setAuthenticated(user, null)
    void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
  }
}

export function useLoginMutation() {
  const onSuccess = useSessionSuccess()
  return useMutation({
    mutationFn: sessionApi.login,
    onSuccess,
  })
}

export function useSignupMutation() {
  const onSuccess = useSessionSuccess()
  return useMutation({
    mutationFn: sessionApi.signup,
    onSuccess,
  })
}

export function useLogoutMutation() {
  const queryClient = useQueryClient()
  const setAnonymous = useSessionStore((state) => state.setAnonymous)

  return useMutation({
    mutationFn: sessionApi.logout,
    onSuccess: () => {
      setAnonymous()
      queryClient.clear()
    },
  })
}

export function useChangePasswordMutation() {
  const updateUser = useSessionStore((state) => state.updateUser)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: sessionApi.changePassword,
    onSuccess: (user) => {
      updateUser(user)
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}

export function usePasswordResetRequestMutation() {
  return useMutation({ mutationFn: sessionApi.requestPasswordReset })
}

export function usePasswordResetConfirmMutation() {
  return useMutation({ mutationFn: sessionApi.confirmPasswordReset })
}

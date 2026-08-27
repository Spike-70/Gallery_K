import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { sessionKeys } from '@/entities/session/api/keys'
import * as sessionApi from '@/entities/session/api/sessionApi'
import * as socialApi from '@/entities/session/api/socialApi'
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
    setAuthenticated(user)
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


// ── 소셜 로그인 (API 문서 §6.11–§6.15·§8.7–§8.8) ───────────────────────────

/**
 * 켜진 제공자 목록. **화면이 환경변수를 알 필요가 없다**(소셜 문서 §8).
 * 배포 중에는 바뀌지 않으므로 세션 정책보다 길게 잡는다.
 */
export function useSocialProvidersQuery() {
  return useQuery({
    queryKey: sessionKeys.socialProviders(),
    queryFn: socialApi.fetchSocialProviders,
    ...CACHE_POLICY.me,
    // 실패해도 화면은 뜬다. 전화번호 로그인이 그대로 남아 있다(FA-7).
    retry: false,
  })
}

export function useSocialLinkMutation() {
  const onSuccess = useSessionSuccess()
  return useMutation({ mutationFn: socialApi.linkSocialAccount, onSuccess })
}

export function useSocialSignupMutation() {
  const onSuccess = useSessionSuccess()
  return useMutation({ mutationFn: socialApi.signupWithSocial, onSuccess })
}

export function useSocialIdentitiesQuery(enabled = true) {
  return useQuery({
    queryKey: sessionKeys.socialIdentities(),
    queryFn: socialApi.fetchSocialIdentities,
    enabled,
    ...CACHE_POLICY.me,
  })
}

export function useUnlinkSocialMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: socialApi.unlinkSocialIdentity,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.socialIdentities() })
      // 마지막 수단 여부가 바뀌므로 세션도 다시 읽는다.
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}

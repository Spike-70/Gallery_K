import { useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useEffect } from 'react'

import { useSessionQuery } from '@/entities/session/api/queries'
import { fetchCurrentExhibition } from '@/entities/exhibition/api/exhibitionApi'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { hasAuthHint, useSessionStore } from '@/entities/session/model/sessionStore'
import { CACHE_POLICY } from '@/shared/api/queryClient'

/**
 * 세션 부트스트랩 — 프런트엔드 아키텍처 문서 §8.2
 *
 * 1. `GET /auth/session`을 1회 호출한다.
 * 2. 결과를 `sessionStore`에 미러링한다(가드가 동기적으로 읽어야 한다).
 *
 * 라우터 렌더를 보류하지 않고 `status: 'booting'`을 노출한다. 보류 판단은
 * 가드가 하며, 그래야 A 첫 화면처럼 세션과 무관한 화면이 먼저 뜬다(FA-7).
 *
 * 미디어 자격은 관리하지 않는다 — 이미지 URL은 응답에 담겨 오는 presigned URL이고,
 * 만료 복구는 `QueryProvider`가 주입하는 이미지 복구 경로가 담당한다(F-12).
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const { data, isSuccess, isError } = useSessionQuery()
  const queryClient = useQueryClient()

  /**
   * 낙관적 병렬 부팅(F-9) — 이전 방문에서 인증된 적이 있으면 세션 확인을 **기다리지 않고**
   * 오늘의 전시를 함께 요청한다. C 화면 도달이 왕복 1회만큼 짧아진다.
   *
   * 세션이 무효로 판명되면 이 결과는 그냥 버려진다. 비회원이 한 번 헛요청하는 비용보다
   * 매일 아침 오는 회원의 1회 왕복이 크다.
   */
  useEffect(() => {
    if (!hasAuthHint()) return
    void queryClient.prefetchQuery({
      queryKey: exhibitionKeys.current(),
      queryFn: fetchCurrentExhibition,
      ...CACHE_POLICY.currentExhibition,
    })
  }, [queryClient])

  const setAuthenticated = useSessionStore((state) => state.setAuthenticated)
  const setAnonymous = useSessionStore((state) => state.setAnonymous)

  useEffect(() => {
    if (isError) {
      // 세션 확인이 실패해도 화면은 뜬다. 비로그인으로 간주한다.
      setAnonymous()
      return
    }
    if (!isSuccess) return
    if (data.isAuthenticated && data.user) {
      setAuthenticated(data.user)
    } else {
      setAnonymous()
    }
  }, [data, isSuccess, isError, setAuthenticated, setAnonymous])

  return <>{children}</>
}

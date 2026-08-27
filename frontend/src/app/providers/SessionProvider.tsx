import { type ReactNode, useCallback, useEffect } from 'react'

import { useSessionQuery } from '@/entities/session/api/queries'
import { refreshMediaSession } from '@/entities/session/api/sessionApi'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { useVisibilityChange } from '@/shared/hooks/useVisibilityChange'
import { logger } from '@/shared/lib/logger'

/**
 * 세션 부트스트랩 — 프런트엔드 아키텍처 문서 §8.2
 *
 * 1. `GET /auth/session`을 1회 호출한다.
 * 2. 결과를 `sessionStore`에 미러링한다(가드가 동기적으로 읽어야 한다).
 * 3. **미디어 서명 쿠키를 유지한다** — 만료 10분 전 또는 포그라운드 복귀 시 갱신.
 *    갱신 실패 시 전 이미지가 403이 되는 단일 실패 지점이다(F-12).
 *
 * 라우터 렌더를 보류하지 않고 `status: 'booting'`을 노출한다. 보류 판단은
 * 가드가 하며, 그래야 A 첫 화면처럼 세션과 무관한 화면이 먼저 뜬다(FA-7).
 */

/** 만료 몇 밀리초 전에 갱신할 것인가 */
const REFRESH_MARGIN_MS = 10 * 60_000

export function SessionProvider({ children }: { children: ReactNode }) {
  const { data, isSuccess, isError } = useSessionQuery()
  const setAuthenticated = useSessionStore((state) => state.setAuthenticated)
  const setAnonymous = useSessionStore((state) => state.setAnonymous)
  const mediaExpiresAt = useSessionStore((state) => state.mediaExpiresAt)
  const status = useSessionStore((state) => state.status)

  useEffect(() => {
    if (isError) {
      // 세션 확인이 실패해도 화면은 뜬다. 비로그인으로 간주한다.
      setAnonymous()
      return
    }
    if (!isSuccess) return
    if (data.isAuthenticated && data.user) {
      setAuthenticated(data.user, data.mediaSessionExpiresAt)
    } else {
      setAnonymous()
    }
  }, [data, isSuccess, isError, setAuthenticated, setAnonymous])

  const ensureMediaSession = useCallback(async () => {
    if (status !== 'authenticated') return
    const expiresAt = mediaExpiresAt ? new Date(mediaExpiresAt).getTime() : 0
    if (expiresAt - Date.now() > REFRESH_MARGIN_MS) return
    try {
      const { expiresAt: renewed } = await refreshMediaSession()
      useSessionStore.setState({ mediaExpiresAt: renewed })
    } catch (error) {
      logger.warn('media session refresh failed', error)
    }
  }, [status, mediaExpiresAt])

  // 만료가 다가오면 갱신한다. 타이머와 포그라운드 복귀 두 경로를 모두 둔다.
  useEffect(() => {
    void ensureMediaSession()
    const timer = window.setInterval(() => void ensureMediaSession(), 60_000)
    return () => window.clearInterval(timer)
  }, [ensureMediaSession])

  useVisibilityChange(useCallback(() => void ensureMediaSession(), [ensureMediaSession]))

  return <>{children}</>
}

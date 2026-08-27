import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useSessionStore } from '@/entities/session/model/sessionStore'
import { paths, loginPathWithNext } from '@/app/router/paths'
import { Spinner } from '@/shared/ui'
import { status as statusMessages } from '@/shared/config/messages'

/**
 * 라우트 가드 — 프런트엔드 아키텍처 문서 §5.3
 *
 * **세션 부트스트랩 완료 후에만 판정한다.** 미완료 상태에서 리다이렉트하면
 * 새로고침마다 로그인 화면이 번쩍인다.
 */

/** 부팅 중 스플래시. 흰 화면을 만들지 않는다(UX §10). */
function BootSplash() {
  return (
    <div className="flex min-h-screen items-center justify-center" role="status" aria-live="polite">
      <Spinner size="lg" label={statusMessages.loading} />
    </div>
  )
}

/** 회원 전용 경로 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const status = useSessionStore((state) => state.status)
  const user = useSessionStore((state) => state.user)
  const location = useLocation()

  if (status === 'booting') return <BootSplash />
  if (status === 'anonymous') {
    return <Navigate to={loginPathWithNext(location.pathname + location.search)} replace />
  }

  // 초기 비밀번호 계정은 교체 전까지 다른 화면으로 갈 수 없다(UX §3.5).
  if (user?.mustChangePassword && location.pathname !== paths.passwordChange) {
    return <Navigate to={paths.passwordChange} replace />
  }

  return <>{children}</>
}

/**
 * 큐레이터 전용 경로.
 * 회원이지만 비큐레이터면 **조용히** 갤러리로 보낸다 — 관리자 존재를 노출하지 않는다.
 * 이는 UI 편의일 뿐 보안이 아니며, 실제 통제는 서버가 한다(PRD §8.4).
 */
export function RequireCurator({ children }: { children: ReactNode }) {
  const status = useSessionStore((state) => state.status)
  const user = useSessionStore((state) => state.user)

  if (status === 'booting') return <BootSplash />
  if (status === 'anonymous') return <Navigate to={paths.login} replace />
  if (user?.role !== 'curator') return <Navigate to={paths.gallery} replace />

  return <>{children}</>
}

/** 로그인·가입 화면에서 이미 세션이 있으면 갤러리로 */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const status = useSessionStore((state) => state.status)

  if (status === 'booting') return <BootSplash />
  if (status === 'authenticated') return <Navigate to={paths.gallery} replace />

  return <>{children}</>
}

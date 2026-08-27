import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'

import { actions, status } from '@/shared/config/messages'
import { useOnlineStatus } from '@/shared/hooks/useOnlineStatus'
import { ErrorState } from '@/shared/ui'

/**
 * 관리자 공통 레이아웃 — 프런트엔드 아키텍처 문서 §3
 *
 * `html[data-surface="studio"]`로 밀도 토큰만 바꾼다. 컴포넌트를 두 벌 만들지 않는다(DS-6).
 * **관리자 화면은 오프라인을 지원하지 않는다.** 명시적으로 안내한다(UX U-13).
 */
export function StudioLayout() {
  const online = useOnlineStatus()

  useEffect(() => {
    document.documentElement.dataset.surface = 'studio'
    return () => {
      delete document.documentElement.dataset.surface
    }
  }, [])

  return (
    <div className="min-h-screen bg-canvas">
      <main id="gk-main" tabIndex={-1} className="gk-container-studio py-6 focus:outline-none">
        {online ? (
          <Outlet />
        ) : (
          <ErrorState
            message={status.adminOffline}
            retryLabel={actions.retry}
            onRetry={() => window.location.reload()}
          />
        )}
      </main>
    </div>
  )
}

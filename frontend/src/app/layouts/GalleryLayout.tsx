import { Outlet } from 'react-router-dom'

import { useOnlineStatus } from '@/shared/hooks/useOnlineStatus'
import { status } from '@/shared/config/messages'
import { Banner } from '@/shared/ui'

/**
 * 관람자 공통 레이아웃 — 프런트엔드 아키텍처 문서 §3
 *
 * 컨테이너 폭은 560px이며 **데스크톱에서도 넓히지 않는다** — 모바일 갤러리의
 * 비례를 유지한다(디자인 시스템 §5.2).
 *
 * 오프라인이어도 화면을 비우지 않는다. 캐시 내용 위에 안내 바만 얹는다(PRD §6.5).
 */
export function GalleryLayout() {
  const online = useOnlineStatus()

  return (
    <div className="min-h-screen bg-canvas">
      {online ? null : (
        <div className="sticky top-0 z-sticky">
          <Banner tone="offline" message={status.offlineBanner} />
        </div>
      )}
      <main id="gk-main" tabIndex={-1} className="gk-container-gallery py-6 focus:outline-none">
        <Outlet />
      </main>
    </div>
  )
}

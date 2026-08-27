import { Outlet } from 'react-router-dom'

import { RouteAnnouncer } from '@/app/providers/RouteAnnouncer'

import { useOnlineStatus } from '@/shared/hooks/useOnlineStatus'
import { status } from '@/shared/config/messages'
import { Banner, TopBackSlot } from '@/shared/ui'

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
        {/* 상단 좌측 `←` 자리. 대상은 화면의 `BackLink`가 채운다(UX §2.3). */}
        <TopBackSlot className="-ml-3 mb-2" />
        <Outlet />
        <RouteAnnouncer />
      </main>
    </div>
  )
}

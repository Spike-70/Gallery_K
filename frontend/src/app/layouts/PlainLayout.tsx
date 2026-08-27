import { Outlet } from 'react-router-dom'

import { RouteAnnouncer } from '@/app/providers/RouteAnnouncer'

import { TopBackSlot } from '@/shared/ui'

/** 단독 화면(A · A-1 · D · 미리보기 · 오류)의 레이아웃 */
export function PlainLayout() {
  return (
    <main id="gk-main" tabIndex={-1} className="relative min-h-screen focus:outline-none">
      {/*
        상단 좌측 `←` 자리 — 대상은 화면의 `BackLink`가 채운다(UX §2.3).
        단독 화면은 세로 가운데 정렬이 많아 흐름에 넣으면 레이아웃이 밀린다. 띄워 둔다.
      */}
      <TopBackSlot className="absolute left-1 top-1 z-sticky" />
      <Outlet />
      <RouteAnnouncer />
    </main>
  )
}

import { Suspense, useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'

import { AppErrorBoundary } from '@/app/providers/AppErrorBoundary'
import { FontScaleProvider } from '@/app/providers/FontScaleProvider'
import { PwaProvider } from '@/app/providers/PwaProvider'
import { QueryProvider } from '@/app/providers/QueryProvider'
import { SessionProvider } from '@/app/providers/SessionProvider'
import { ToastProvider } from '@/app/providers/ToastProvider'
import { prefetchAuthChunk, router } from '@/app/router'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { registerSessionLostHandler } from '@/shared/api/httpClient'
import { paths } from '@/shared/config/paths'
import { status } from '@/shared/config/messages'
import { ScreenSkeleton } from '@/shared/ui'

/**
 * 애플리케이션 셸 — 프런트엔드 아키텍처 문서 §8.2
 *
 * 프로바이더 조립 순서에 의미가 있다.
 *  ErrorBoundary → Query → Session → FontScale → Toast → PWA → Router
 *  세션이 폰트 스케일의 원천이고, 토스트는 라우터 밖에서도 떠야 한다.
 *  PWA는 세션(푸시 구독 재검증)과 토스트를 모두 필요로 하므로 그 안쪽에 둔다.
 */
function SessionLostBridge() {
  const setAnonymous = useSessionStore((state) => state.setAnonymous)

  useEffect(() => {
    // `shared`는 상위 레이어를 알 수 없으므로 세션 소실 처리를 여기서 주입한다(§7.1).
    registerSessionLostHandler(() => {
      setAnonymous()
      window.location.assign(paths.login)
    })
  }, [setAnonymous])

  return null
}

/** 라우트 청크를 받는 동안의 자리. 전체 화면 스피너를 쓰지 않는다(DS §10). */
function RouteFallback() {
  return <ScreenSkeleton label={status.loading} />
}

export function App() {
  useEffect(() => {
    prefetchAuthChunk()
  }, [])

  return (
    <AppErrorBoundary>
      <QueryProvider>
        <SessionLostBridge />
        <SessionProvider>
          <FontScaleProvider>
            <ToastProvider>
              <PwaProvider>
                <Suspense fallback={<RouteFallback />}>
                  <RouterProvider router={router} />
                </Suspense>
              </PwaProvider>
            </ToastProvider>
          </FontScaleProvider>
        </SessionProvider>
      </QueryProvider>
    </AppErrorBoundary>
  )
}

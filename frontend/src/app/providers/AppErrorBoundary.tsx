import { Component, type ErrorInfo, type ReactNode } from 'react'

import { isApiError } from '@/shared/api/ApiError'
import { actions, screens } from '@/shared/config/messages'
import { logger } from '@/shared/lib/logger'
import { ErrorState } from '@/shared/ui'

/**
 * 루트 오류 경계 — 프런트엔드 아키텍처 문서 §13
 *
 * 렌더 예외를 전체 화면 `ErrorState`로 바꾸고 새로고침을 유도한다.
 * `request_id`가 있으면 `문의 번호`로 병기한다. **그 외 기술 정보는 노출하지 않는다**(UX §3.19).
 *
 * 청크 로드 실패는 배포 직후 흔한 문제이므로 자동으로 1회 새로고침한다.
 */
type Props = { children: ReactNode }
type State = { error: Error | null }

const CHUNK_RELOAD_KEY = 'gk.chunk-reloaded'

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    logger.error('render error', error, info.componentStack)

    const isChunkError = /Loading chunk|dynamically imported module|Failed to fetch/i.test(error.message)
    if (isChunkError && sessionStorage.getItem(CHUNK_RELOAD_KEY) !== '1') {
      sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
      window.location.reload()
    }
  }

  render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <main className="gk-container-gallery flex min-h-screen items-center justify-center">
        <ErrorState
          message={screens.errors.renderErrorTitle}
          retryLabel={actions.refresh}
          onRetry={() => window.location.reload()}
          requestId={isApiError(error) ? error.requestId : null}
        />
      </main>
    )
  }
}

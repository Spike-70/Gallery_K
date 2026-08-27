import { useRouteError } from 'react-router-dom'

import { isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { BackLink, ErrorState } from '@/shared/ui'

/**
 * 라우트 오류 경계 — 프런트엔드 아키텍처 문서 §13
 * 해당 라우트만 대체하고 다른 화면으로 이동은 가능한 상태를 유지한다.
 * `request_id`는 `문의 번호`라는 라벨로만 노출한다(UX §3.19).
 */
export function RouteErrorPage() {
  const error = useRouteError()

  return (
    <div className="gk-container-gallery flex min-h-screen flex-col justify-center">
      <ErrorState
        message={isApiError(error) ? resolveErrorMessage(error) : screens.errors.renderErrorTitle}
        retryLabel={actions.refresh}
        onRetry={() => window.location.reload()}
        requestId={isApiError(error) ? error.requestId : null}
      />
      <BackLink to={paths.landing} label={actions.backHome} />
    </div>
  )
}

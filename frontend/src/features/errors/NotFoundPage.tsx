import { actions, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { BackLink, EmptyState } from '@/shared/ui'

/** 404 — UX 설계서 §3.19. 기술 정보를 노출하지 않는다. */
export function NotFoundPage() {
  return (
    <div className="gk-container-gallery flex min-h-screen flex-col justify-center">
      <EmptyState message={screens.errors.notFoundTitle} icon="info" />
      <BackLink to={paths.landing} label={actions.backHome} />
    </div>
  )
}

import type { ReactNode } from 'react'

import { status } from '@/shared/config/messages'
import { usePullToRefresh } from '@/shared/hooks/usePullToRefresh'
import { Spinner } from '@/shared/ui/Spinner'

/**
 * 당겨서 새로고침 — UX 설계서 §7 (C · C-3)
 *
 * 제스처의 시각 표현을 한곳에 모은다. 화면은 "무엇을 갱신할지"만 말하면 된다.
 * 인라인 `style`은 **제스처 transform에 한해** 허용된다(디자인 시스템 §11.4).
 */
export type PullToRefreshProps = {
  onRefresh: () => Promise<unknown> | void
  disabled?: boolean
  children: ReactNode
}

export function PullToRefresh({ onRefresh, disabled, children }: PullToRefreshProps) {
  const pull = usePullToRefresh({ onRefresh, disabled })

  return (
    <div
      {...pull.handlers}
      className="transition-transform duration-fast ease-standard"
      style={{ transform: pull.distance ? `translateY(${pull.distance}px)` : undefined }}
    >
      {pull.refreshing || pull.armed ? (
        <div className="flex justify-center py-2" role="status">
          <Spinner size="sm" label={status.loading} />
        </div>
      ) : null}
      {children}
    </div>
  )
}

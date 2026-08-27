import { type PointerEvent as ReactPointerEvent, useCallback, useRef, useState } from 'react'

import { GESTURE } from '@/shared/config/constants'

/**
 * 당겨서 새로고침 — UX 설계서 §7
 *
 * 임계 80px. **맨 위에 있을 때만** 반응한다 — 목록 중간에서 아래로 미는 것은 스크롤이다.
 *
 * 이 제스처에도 대체 수단이 있어야 한다(UX-7). 화면은 오류 상태에서 `다시 시도` 버튼을
 * 함께 제공하며, 이 훅은 그것을 대신하지 않는다.
 */
export type UsePullToRefreshOptions = {
  onRefresh: () => Promise<unknown> | void
  /** 이미 갱신 중이면 다시 당겨도 무시한다 */
  disabled?: boolean
}

export function usePullToRefresh({ onRefresh, disabled }: UsePullToRefreshOptions) {
  const startY = useRef<number | null>(null)
  const [distance, setDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  const onPointerDown = useCallback(
    (event: ReactPointerEvent) => {
      if (disabled || refreshing) return
      // 맨 위가 아니면 스크롤이다. 손대지 않는다.
      if (window.scrollY > 0) return
      startY.current = event.clientY
    },
    [disabled, refreshing],
  )

  const onPointerMove = useCallback((event: ReactPointerEvent) => {
    if (startY.current === null) return
    const delta = event.clientY - startY.current
    if (delta <= 0) {
      setDistance(0)
      return
    }
    // 고무줄 저항 — 끝없이 늘어나지 않는다.
    setDistance(Math.min(GESTURE.pullDistance * 1.5, delta / 2))
  }, [])

  const onPointerUp = useCallback(() => {
    const pulled = distance
    startY.current = null
    setDistance(0)
    if (pulled < GESTURE.pullDistance) return

    setRefreshing(true)
    void Promise.resolve(onRefresh()).finally(() => setRefreshing(false))
  }, [distance, onRefresh])

  return {
    distance,
    refreshing,
    /** 임계를 넘겼는가 — 놓으면 갱신된다는 신호를 화면이 그릴 수 있다 */
    armed: distance >= GESTURE.pullDistance,
    handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp },
  }
}

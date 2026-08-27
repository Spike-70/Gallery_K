import { type PointerEvent as ReactPointerEvent, useCallback, useRef, useState } from 'react'

import { GESTURE } from '@/shared/config/constants'

/**
 * 스와이프 — UX 설계서 §7
 *
 * 임계: 화면 폭의 20% 또는 속도 0.4px/ms. 이동 중에는 손가락을 그대로 따라가고
 * 놓는 순간 정착한다. **모든 제스처에는 대체 수단이 있다**(UX-7) — 이 훅은
 * 대체 수단을 대신하지 않으며, 화면이 링크·키보드 조작을 함께 제공해야 한다.
 */
export type SwipeDirection = 'left' | 'right' | 'down'

export type UseSwipeOptions = {
  onSwipe: (direction: SwipeDirection) => void
  /** 좌우 스와이프 사용 여부 */
  horizontal?: boolean
  /** 아래로 스와이프(뷰어 닫기) 사용 여부 */
  vertical?: boolean
  /** 양 끝에서 고무줄 저항을 줄지 판단한다. `false`면 이동량을 1/3로 줄인다. */
  canSwipe?: (direction: SwipeDirection) => boolean
}

export function useSwipe({ onSwipe, horizontal = true, vertical = false, canSwipe }: UseSwipeOptions) {
  const start = useRef<{ x: number; y: number; time: number } | null>(null)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)

  const onPointerDown = useCallback((event: ReactPointerEvent) => {
    start.current = { x: event.clientX, y: event.clientY, time: performance.now() }
    setDragging(true)
  }, [])

  const onPointerMove = useCallback(
    (event: ReactPointerEvent) => {
      if (!start.current) return
      const dx = event.clientX - start.current.x
      const dy = event.clientY - start.current.y

      if (horizontal) {
        const direction: SwipeDirection = dx < 0 ? 'left' : 'right'
        const resistance = canSwipe && !canSwipe(direction) ? 3 : 1
        setOffset({ x: dx / resistance, y: 0 })
      } else if (vertical && dy > 0) {
        setOffset({ x: 0, y: dy })
      }
    },
    [horizontal, vertical, canSwipe],
  )

  const onPointerUp = useCallback(
    (event: ReactPointerEvent) => {
      const origin = start.current
      start.current = null
      setDragging(false)
      setOffset({ x: 0, y: 0 })
      if (!origin) return

      const dx = event.clientX - origin.x
      const dy = event.clientY - origin.y
      const elapsed = Math.max(1, performance.now() - origin.time)

      if (vertical && dy > 0) {
        const passed = dy > GESTURE.dismissDistance || dy / elapsed > GESTURE.dismissVelocity
        if (passed) onSwipe('down')
        return
      }

      if (!horizontal) return
      const threshold = window.innerWidth * GESTURE.swipeRatio
      const velocity = Math.abs(dx) / elapsed
      if (Math.abs(dx) > threshold || velocity > GESTURE.swipeVelocity) {
        onSwipe(dx < 0 ? 'left' : 'right')
      }
    },
    [horizontal, vertical, onSwipe],
  )

  return {
    offset,
    dragging,
    handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp },
  }
}

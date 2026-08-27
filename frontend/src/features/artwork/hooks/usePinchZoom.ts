import { type PointerEvent as ReactPointerEvent, useCallback, useRef, useState } from 'react'

import { GESTURE } from '@/shared/config/constants'

/**
 * 핀치 줌 · 더블탭 · 패닝 — UX 설계서 §3.8·§7
 *
 * 배율 1.0–4.0. 더블탭은 2배 토글. 확대 상태에서 드래그로 이동한다.
 * **제스처를 모르는 사용자를 위해 `크게 보기` 버튼이 병존한다**(UX-7) — 이 훅은
 * 대체 수단을 대신하지 않는다.
 */
export type ZoomState = { scale: number; x: number; y: number }

const IDLE: ZoomState = { scale: 1, x: 0, y: 0 }

export function usePinchZoom() {
  const [state, setState] = useState<ZoomState>(IDLE)
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const pinchStart = useRef<{ distance: number; scale: number } | null>(null)
  const panStart = useRef<{ x: number; y: number; originX: number; originY: number } | null>(null)
  const lastTap = useRef(0)

  const reset = useCallback(() => setState(IDLE), [])

  const distanceBetween = () => {
    const [a, b] = Array.from(pointers.current.values())
    return Math.hypot(a.x - b.x, a.y - b.y)
  }

  const onPointerDown = useCallback(
    (event: ReactPointerEvent) => {
      pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY })

      if (pointers.current.size === 2) {
        pinchStart.current = { distance: distanceBetween(), scale: state.scale }
        panStart.current = null
        return
      }

      // 더블탭 — 2배 토글
      const now = performance.now()
      if (now - lastTap.current < GESTURE.doubleTapMs) {
        setState((current) => (current.scale > 1 ? IDLE : { scale: 2, x: 0, y: 0 }))
        lastTap.current = 0
        return
      }
      lastTap.current = now

      if (state.scale > 1) {
        panStart.current = { x: event.clientX, y: event.clientY, originX: state.x, originY: state.y }
      }
    },
    [state],
  )

  const onPointerMove = useCallback((event: ReactPointerEvent) => {
    if (!pointers.current.has(event.pointerId)) return
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY })

    if (pointers.current.size === 2 && pinchStart.current) {
      const ratio = distanceBetween() / pinchStart.current.distance
      const scale = Math.min(GESTURE.zoomMax, Math.max(1, pinchStart.current.scale * ratio))
      setState((current) => ({ ...current, scale }))
      return
    }

    if (panStart.current) {
      setState((current) => ({
        ...current,
        x: panStart.current!.originX + (event.clientX - panStart.current!.x),
        y: panStart.current!.originY + (event.clientY - panStart.current!.y),
      }))
    }
  }, [])

  const onPointerUp = useCallback((event: ReactPointerEvent) => {
    pointers.current.delete(event.pointerId)
    if (pointers.current.size < 2) pinchStart.current = null
    if (pointers.current.size === 0) {
      panStart.current = null
      // 원래 배율로 돌아오면 위치도 초기화한다.
      setState((current) => (current.scale <= 1 ? IDLE : current))
    }
  }, [])

  /** `크게 보기` 버튼 등 제스처 대체 수단이 호출한다 */
  const toggleZoom = useCallback(() => {
    setState((current) => (current.scale > 1 ? IDLE : { scale: 2, x: 0, y: 0 }))
  }, [])

  return {
    zoom: state,
    reset,
    toggleZoom,
    isZoomed: state.scale > 1,
    handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp },
  }
}

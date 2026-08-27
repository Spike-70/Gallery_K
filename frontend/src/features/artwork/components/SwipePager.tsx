import type { ReactNode } from 'react'

import { useSwipe } from '@/shared/hooks/useSwipe'

/**
 * SwipePager — UX 설계서 §3.8
 *
 * 손가락 이동을 그대로 따라가고 놓으면 260ms로 정착한다. 양 끝에서는 고무줄 저항을
 * 주되 **순환하지 않는다**(UX-2).
 *
 * 전환 중 **텍스트도 함께 이동한다** — 그림만 바뀌면 어떤 설명인지 혼동된다.
 */
export type SwipePagerProps = {
  canGoPrev: boolean
  canGoNext: boolean
  onPrev: () => void
  onNext: () => void
  children: ReactNode
}

export function SwipePager({ canGoPrev, canGoNext, onPrev, onNext, children }: SwipePagerProps) {
  const { offset, dragging, handlers } = useSwipe({
    onSwipe: (direction) => {
      if (direction === 'left') onNext()
      if (direction === 'right') onPrev()
    },
    canSwipe: (direction) => (direction === 'left' ? canGoNext : canGoPrev),
  })

  return (
    <div
      {...handlers}
      className="touch-pan-y"
      style={{
        transform: offset.x ? `translateX(${offset.x}px)` : undefined,
        transition: dragging ? 'none' : 'transform var(--gk-duration-base) var(--gk-ease-standard)',
      }}
    >
      {children}
    </div>
  )
}

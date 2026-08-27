import type { ReactNode } from 'react'

import { useSwipe } from '@/shared/hooks/useSwipe'

/**
 * SwipePager — UX 설계서 §3.8
 *
 * 손가락 이동을 그대로 따라가고 놓으면 260ms로 정착한다. 양 끝에서는 고무줄 저항을
 * 주되 **순환하지 않는다**(UX-2).
 *
 * **이동 중 이웃 그림이 따라 들어온다.** 이웃은 화면 밖(`left-full`/`right-full`)에
 * 절대 배치되므로 컨테이너 높이는 **현재 그림만** 결정한다 — 설명 길이가 다른 이웃 때문에
 * 화면이 튀지 않는다.
 *
 * 전환 중 **텍스트도 함께 이동한다** — 그림만 바뀌면 어떤 설명인지 혼동된다.
 */
export type SwipePagerProps = {
  canGoPrev: boolean
  canGoNext: boolean
  onPrev: () => void
  onNext: () => void
  /** 따라 들어올 이웃. 캐시에 없으면 `null`이며 그때는 현재 그림만 움직인다. */
  prevPeek?: ReactNode
  nextPeek?: ReactNode
  children: ReactNode
}

export function SwipePager({
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  prevPeek,
  nextPeek,
  children,
}: SwipePagerProps) {
  const { offset, dragging, handlers } = useSwipe({
    onSwipe: (direction) => {
      if (direction === 'left') onNext()
      if (direction === 'right') onPrev()
    },
    canSwipe: (direction) => (direction === 'left' ? canGoNext : canGoPrev),
  })

  return (
    <div className="overflow-hidden">
      <div
        {...handlers}
        className="relative touch-pan-y"
        style={{
          transform: offset.x ? `translateX(${offset.x}px)` : undefined,
          transition: dragging ? 'none' : 'transform var(--gk-duration-base) var(--gk-ease-standard)',
        }}
      >
        {/* 이웃은 흐름 밖에 둔다. 드래그 중에만 가장자리로 들어온다. */}
        {prevPeek ? (
          <div aria-hidden className="absolute right-full top-0 w-full pr-4">
            {prevPeek}
          </div>
        ) : null}

        {children}

        {nextPeek ? (
          <div aria-hidden className="absolute left-full top-0 w-full pl-4">
            {nextPeek}
          </div>
        ) : null}
      </div>
    </div>
  )
}

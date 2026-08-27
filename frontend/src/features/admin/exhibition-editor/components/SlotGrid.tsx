import { type PointerEvent as ReactPointerEvent, useCallback, useRef, useState } from 'react'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { SlotButton } from '@/features/admin/exhibition-editor/components/SlotButton'
import type { UploadProgress } from '@/features/admin/exhibition-editor/hooks/useUploadQueue'
import { GESTURE } from '@/shared/config/constants'
import { paths } from '@/shared/config/paths'
import type { IsoDate } from '@/shared/types/utility'

/**
 * 12칸 슬롯 그리드 — 디자인 시스템 문서 §5.3·§8.3
 *
 * `slots`가 **항상 12개**라는 서버 계약이 이 화면을 단순하게 만든다(API 문서 §9.3).
 *
 * 순서 변경(UX §3.12)
 *  - **모바일: 롱프레스(400ms) 후 드래그.** HTML5 `draggable`은 터치에서 아예 동작하지
 *    않는다 — 모바일 우선 제품에서 그것은 기능이 없는 것과 같다. 포인터 이벤트로 직접 다룬다.
 *  - **PC: 즉시 드래그.**
 *  - **키보드: `Space`로 집고 방향키로 옮기고 `Space`로 놓는다.** `Esc`는 취소.
 *
 * 변경은 최종 상태 선언으로 서버에 보낸다 — 부분 이동 지시가 아니라서 재시도가 안전하다.
 */
export type SlotGridProps = {
  date: IsoDate
  slots: AdminSlot[]
  progress: UploadProgress
  onReorder: (order: { artworkId: string; position: number }[]) => void
  /** 넓은 화면에서는 이동 대신 선택한다(UX §3.12 ≥1024px) */
  selectable?: boolean
  selectedPosition?: number
  onSelect?: (position: number) => void
  onReupload?: () => void
}

/** 포인터 좌표 아래의 슬롯 번호를 찾는다. 드래그 중 어디에 놓일지 판정하는 유일한 수단이다. */
function positionAtPoint(x: number, y: number): number | null {
  const element = document.elementFromPoint(x, y)
  const host = element?.closest('[data-slot-position]')
  const value = host?.getAttribute('data-slot-position')
  return value ? Number(value) : null
}

export function SlotGrid({
  date,
  slots,
  progress,
  onReorder,
  selectable,
  selectedPosition,
  onSelect,
  onReupload,
}: SlotGridProps) {
  const [grabbed, setGrabbed] = useState<number | null>(null)
  const [dropTarget, setDropTarget] = useState<number | null>(null)
  const longPressTimer = useRef<number | null>(null)
  const dragged = useRef(false)

  const move = useCallback(
    (fromPosition: number, toPosition: number) => {
      if (fromPosition === toPosition) return
      const filled = slots.filter((slot) => slot.artworkId)
      const source = slots.find((slot) => slot.position === fromPosition)
      if (!source?.artworkId) return

      const rest = filled.filter((slot) => slot.position !== fromPosition)
      const targetIndex = Math.max(0, Math.min(rest.length, toPosition - 1))
      const ordered = [...rest.slice(0, targetIndex), source, ...rest.slice(targetIndex)]

      onReorder(ordered.map((slot, index) => ({ artworkId: slot.artworkId as string, position: index + 1 })))
    },
    [slots, onReorder],
  )

  const cancelLongPress = () => {
    if (longPressTimer.current !== null) {
      window.clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }

  const endDrag = useCallback(() => {
    cancelLongPress()
    if (grabbed !== null && dropTarget !== null) move(grabbed, dropTarget)
    setGrabbed(null)
    setDropTarget(null)
  }, [grabbed, dropTarget, move])

  const handlePointerDown = (slot: AdminSlot) => (event: ReactPointerEvent) => {
    if (!slot.artworkId) return
    dragged.current = false

    const begin = () => {
      setGrabbed(slot.position)
      setDropTarget(slot.position)
    }

    // 마우스는 즉시, 손가락·펜은 롱프레스 뒤에 집는다 — 스크롤과 구분해야 한다.
    if (event.pointerType === 'mouse') begin()
    else longPressTimer.current = window.setTimeout(begin, GESTURE.longPressMs)
  }

  const handlePointerMove = (event: ReactPointerEvent) => {
    if (grabbed === null) {
      // 롱프레스가 걸리기 전에 움직이면 스크롤 의도다. 집기를 취소한다.
      cancelLongPress()
      return
    }
    dragged.current = true
    const over = positionAtPoint(event.clientX, event.clientY)
    if (over) setDropTarget(over)
  }

  const handleKeyDown = (slot: AdminSlot) => (event: React.KeyboardEvent) => {
    if (!slot.artworkId) return

    if (event.key === ' ' || event.key === 'Spacebar') {
      event.preventDefault()
      if (grabbed === null) {
        setGrabbed(slot.position)
        setDropTarget(slot.position)
        return
      }
      endDrag()
      return
    }

    if (event.key === 'Escape' && grabbed !== null) {
      event.preventDefault()
      setGrabbed(null)
      setDropTarget(null)
      return
    }

    if (grabbed === null || dropTarget === null) return
    const step = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0
    if (step === 0) return
    event.preventDefault()
    setDropTarget(Math.max(1, Math.min(slots.length, dropTarget + step)))
  }

  return (
    <ul
      className="grid list-none grid-cols-3 gap-3 p-0"
      onPointerMove={handlePointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onPointerLeave={cancelLongPress}
      // 드래그로 끝난 포인터는 이동·선택을 일으키지 않는다.
      onClickCapture={(event) => {
        if (dragged.current) {
          event.preventDefault()
          event.stopPropagation()
          dragged.current = false
        }
      }}
    >
      {slots.map((slot) => (
        <li key={slot.position}>
          <SlotButton
            slot={slot}
            to={selectable ? undefined : paths.adminExhibitionSlot(date, slot.position)}
            onSelect={selectable && onSelect ? () => onSelect(slot.position) : undefined}
            selected={selectable ? slot.position === selectedPosition : undefined}
            progress={progress[slot.position]}
            grabbed={grabbed === slot.position}
            dropTarget={grabbed !== null && dropTarget === slot.position && grabbed !== slot.position}
            onReupload={onReupload}
            onPointerDownCapture={handlePointerDown(slot)}
            onKeyDown={handleKeyDown(slot)}
          />
        </li>
      ))}
    </ul>
  )
}

import { useState } from 'react'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { SlotButton } from '@/features/admin/exhibition-editor/components/SlotButton'
import type { UploadProgress } from '@/features/admin/exhibition-editor/hooks/useUploadQueue'
import type { IsoDate } from '@/shared/types/utility'
import { paths } from '@/shared/config/paths'

/**
 * 12칸 슬롯 그리드 — 디자인 시스템 문서 §5.3·§8.3
 *
 * `slots`가 **항상 12개**라는 서버 계약이 이 화면을 단순하게 만든다(API 문서 §9.3).
 *
 * 순서 변경: 드래그(PC·모바일) + **방향키 대체 조작**(UX-7).
 * 변경은 최종 상태 선언으로 서버에 보낸다 — 부분 이동 지시가 아니라서 재시도가 안전하다.
 */
export type SlotGridProps = {
  date: IsoDate
  slots: AdminSlot[]
  progress: UploadProgress
  onReorder: (order: { artworkId: string; position: number }[]) => void
}

export function SlotGrid({ date, slots, progress, onReorder }: SlotGridProps) {
  const [dragFrom, setDragFrom] = useState<number | null>(null)

  const move = (fromPosition: number, toPosition: number) => {
    if (fromPosition === toPosition) return
    const filled = slots.filter((slot) => slot.artworkId)
    const source = slots.find((slot) => slot.position === fromPosition)
    if (!source?.artworkId) return

    const rest = filled.filter((slot) => slot.position !== fromPosition)
    const targetIndex = Math.max(0, Math.min(rest.length, toPosition - 1))
    const ordered = [...rest.slice(0, targetIndex), source, ...rest.slice(targetIndex)]

    onReorder(ordered.map((slot, index) => ({ artworkId: slot.artworkId as string, position: index + 1 })))
  }

  return (
    <ul className="grid list-none grid-cols-3 gap-3 p-0">
      {slots.map((slot) => (
        <li key={slot.position}>
          <SlotButton
            slot={slot}
            to={paths.adminExhibitionSlot(date, slot.position)}
            progress={progress[slot.position]}
            grabbed={dragFrom === slot.position}
            onDragStart={() => setDragFrom(slot.position)}
            onDrop={() => {
              if (dragFrom !== null) move(dragFrom, slot.position)
              setDragFrom(null)
            }}
            onKeyboardMove={(direction) => move(slot.position, slot.position + direction)}
          />
        </li>
      ))}
    </ul>
  )
}

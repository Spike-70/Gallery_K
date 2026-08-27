import { Link } from 'react-router-dom'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { slotVisualState } from '@/entities/exhibition/model/admin'
import { screens } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Icon, ProgressRing, Spinner } from '@/shared/ui'

/**
 * SlotButton — 디자인 시스템 문서 §8.3
 *
 * **시각 상태 6종**: `empty` / `uploading` / `processing` / `ready·미완성` /
 * `ready·완성` / `failed`. 서버 `image_status` 5종에 메타데이터 완성 여부가 곱해진다(S-9).
 */
export type SlotButtonProps = {
  slot: AdminSlot
  to: string
  progress?: number
  onDragStart?: () => void
  onDrop?: () => void
  onKeyboardMove?: (direction: -1 | 1) => void
  grabbed?: boolean
}

export function SlotButton({ slot, to, progress, onDragStart, onDrop, onKeyboardMove, grabbed }: SlotButtonProps) {
  const state = slotVisualState(slot)

  return (
    <Link
      to={to}
      draggable={Boolean(slot.artworkId)}
      onDragStart={onDragStart}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault()
        onDrop?.()
      }}
      onKeyDown={(event) => {
        // 드래그의 키보드 대체 조작 — 방향키로 이동(UX-7)
        if (!onKeyboardMove) return
        if (event.key === 'ArrowLeft') {
          event.preventDefault()
          onKeyboardMove(-1)
        }
        if (event.key === 'ArrowRight') {
          event.preventDefault()
          onKeyboardMove(1)
        }
      }}
      aria-grabbed={grabbed}
      className={cn(
        'relative flex aspect-square items-center justify-center overflow-hidden rounded-md border',
        state === 'empty' && 'border-dashed border-border-strong bg-surface',
        state === 'failed' && 'border-danger',
        state !== 'empty' && state !== 'failed' && 'border-border-default bg-subtle',
        grabbed && 'ring-2 ring-border-focus',
      )}
    >
      {slot.image ? (
        <img
          src={slot.image.thumbUrl}
          alt=""
          className={cn('h-full w-full object-cover', state === 'processing' && 'blur-sm')}
        />
      ) : null}

      {state === 'empty' ? (
        <span className="flex flex-col items-center gap-1 text-tertiary">
          <Icon name="plus" size="md" />
          <span className="tabular text-caption">{slot.position}</span>
        </span>
      ) : null}

      {state === 'uploading' ? (
        <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-surface/80">
          <ProgressRing value={progress ?? null} size="md" label={screens.editor.slotUploading} />
          <span className="text-caption text-tertiary">{screens.editor.slotUploading}</span>
        </span>
      ) : null}

      {state === 'processing' ? (
        <span className="absolute inset-0 flex flex-col items-center justify-center gap-1">
          <Spinner size="md" />
          <span className="text-caption text-tertiary">{screens.editor.slotProcessing}</span>
        </span>
      ) : null}

      {state === 'incomplete' ? (
        <span
          aria-label="설명이 아직 없습니다"
          className="absolute right-1 top-1 h-2 w-2 rounded-full bg-empty"
        />
      ) : null}

      {state === 'complete' ? (
        <span className="absolute right-1 top-1 rounded-full bg-surface p-px">
          <Icon name="check" size="sm" className="h-4 w-4 text-published" />
        </span>
      ) : null}

      {state === 'failed' ? (
        <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-surface/90">
          <Icon name="alert" size="md" className="text-danger" />
          <span className="text-caption text-danger">{screens.editor.slotFailed}</span>
        </span>
      ) : null}
    </Link>
  )
}

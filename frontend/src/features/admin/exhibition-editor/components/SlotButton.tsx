import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { slotVisualState } from '@/entities/exhibition/model/admin'
import { actions, landmarks, screens } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Icon, ProgressRing, Spinner } from '@/shared/ui'

/**
 * SlotButton — 디자인 시스템 문서 §8.3
 *
 * **시각 상태 6종**: `empty` / `uploading` / `processing` / `ready·미완성` /
 * `ready·완성` / `failed`. 서버 `image_status` 5종에 메타데이터 완성 여부가 곱해진다(S-9).
 *
 * 미완성은 **점과 `N`을 함께** 쓴다. 점만 두면 색 단독 표기가 되어 DS-5를 어긴다.
 *
 * 모바일에서는 슬롯을 눌러 B-2-2로 가고, 넓은 화면에서는 우측 패널에 **선택**된다 —
 * 화면 이동 없이 12점을 연속 입력하기 위해서다(UX §3.12 ≥1024px).
 */
export type SlotButtonProps = {
  slot: AdminSlot
  /** 이동 대상. `onSelect`가 있으면 무시된다. */
  to?: string
  /** 넓은 화면의 선택 동작 */
  onSelect?: () => void
  selected?: boolean
  progress?: number
  grabbed?: boolean
  dropTarget?: boolean
  onReupload?: () => void
  onPointerDownCapture?: (event: ReactPointerEvent) => void
  onKeyDown?: (event: React.KeyboardEvent) => void
}

function SlotSurface({
  slot,
  progress,
  onReupload,
}: {
  slot: AdminSlot
  progress?: number
  onReupload?: () => void
}): ReactNode {
  const state = slotVisualState(slot)

  return (
    <>
      {slot.image ? (
        <img
          src={slot.image.thumbUrl}
          alt=""
          draggable={false}
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

      {/* 미완성 — 주황 점 + `N`. 색만으로 말하지 않는다(DS-5, GAP-15). */}
      {state === 'incomplete' ? (
        <span
          aria-label={landmarks.slotIncomplete}
          className="absolute right-1 top-1 flex items-center gap-1 rounded-sm bg-surface px-1 text-caption text-empty"
        >
          <span aria-hidden className="h-2 w-2 rounded-full bg-empty" />
          {screens.editor.slotIncompleteMark}
        </span>
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
          {/* 실패한 자리에서 곧바로 다시 올린다. 처음부터 다시 시키지 않는다(UX §10). */}
          {onReupload ? (
            <span
              role="button"
              tabIndex={-1}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                onReupload()
              }}
              className="text-caption text-accent underline underline-offset-4"
            >
              {actions.reupload}
            </span>
          ) : null}
        </span>
      ) : null}
    </>
  )
}

export function SlotButton({
  slot,
  to,
  onSelect,
  selected,
  progress,
  grabbed,
  dropTarget,
  onReupload,
  onPointerDownCapture,
  onKeyDown,
}: SlotButtonProps) {
  const state = slotVisualState(slot)

  const className = cn(
    'relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-md border',
    'touch-none select-none',
    state === 'empty' && 'border-dashed border-border-strong bg-surface',
    state === 'failed' && 'border-danger',
    state !== 'empty' && state !== 'failed' && 'border-border-default bg-subtle',
    selected && 'border-accent',
    grabbed && 'opacity-60 ring-2 ring-border-focus',
    dropTarget && 'ring-2 ring-accent',
  )

  const shared = {
    className,
    'data-slot-position': slot.position,
    onPointerDown: onPointerDownCapture,
    onKeyDown,
  } as const

  if (onSelect) {
    return (
      <button type="button" aria-current={selected || undefined} onClick={onSelect} {...shared}>
        <SlotSurface slot={slot} progress={progress} onReupload={onReupload} />
      </button>
    )
  }

  return (
    <Link to={to ?? '.'} {...shared}>
      <SlotSurface slot={slot} progress={progress} onReupload={onReupload} />
    </Link>
  )
}

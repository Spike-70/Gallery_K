import { type ReactNode, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import { actions } from '@/shared/config/messages'
import { useFocusTrap } from '@/shared/hooks/useFocusTrap'
import { useLockBodyScroll } from '@/shared/hooks/useLockBodyScroll'
import { useSwipe } from '@/shared/hooks/useSwipe'
import { IconButton } from '@/shared/ui/IconButton'

/**
 * BottomSheet — 선택·입력(디자인 시스템 문서 §8.1)
 * 닫기: backdrop 클릭 · `Esc` · 닫기 버튼 · 아래로 스와이프.
 */
export type BottomSheetProps = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

export function BottomSheet({ open, title, onClose, children }: BottomSheetProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  useLockBodyScroll(open)
  useFocusTrap(panelRef, open)

  const { offset, dragging, handlers } = useSwipe({
    horizontal: false,
    vertical: true,
    onSwipe: (direction) => {
      if (direction === 'down') onClose()
    },
  })

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-sheet flex items-end justify-center">
      <div className="absolute inset-0 bg-overlay animate-fade-in" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gk-sheet-title"
        className="relative max-h-[80vh] w-full max-w-gallery overflow-y-auto rounded-t-lg bg-surface pb-6 shadow-sheet animate-sheet-in"
        style={{
          // 손가락 이동을 그대로 따라간다(§6 규칙 4).
          transform: offset.y ? `translateY(${offset.y}px)` : undefined,
          transition: dragging ? 'none' : undefined,
        }}
      >
        <div className="flex items-center justify-between border-b border-border-default px-4 py-2" {...handlers}>
          <h2 id="gk-sheet-title" className="text-title-sm text-primary">
            {title}
          </h2>
          <IconButton icon="close" label={actions.close} onClick={onClose} />
        </div>
        <div className="px-4 pt-4">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

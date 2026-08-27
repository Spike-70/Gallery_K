import { type ReactNode, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import { actions } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { useFocusTrap } from '@/shared/hooks/useFocusTrap'
import { useLockBodyScroll } from '@/shared/hooks/useLockBodyScroll'
import { Button } from '@/shared/ui/Button'

/**
 * Dialog — 확인이 필요한 결정(디자인 시스템 문서 §8.1)
 *
 * 파괴적 동작은 확인 버튼을 `danger`로, **취소를 좌측·기본 포커스**로 둔다(UX-6).
 * 확인은 한 번만 받는다. 문구 입력 같은 추가 관문을 두지 않는다(UX §3.10).
 */
export type DialogProps = {
  open: boolean
  title: string
  description?: ReactNode
  confirmLabel: string
  cancelLabel?: string
  destructive?: boolean
  loading?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function Dialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = actions.cancel,
  destructive = false,
  loading = false,
  onConfirm,
  onClose,
}: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  useLockBodyScroll(open)
  useFocusTrap(panelRef, open)

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
    <div className="fixed inset-0 z-dialog flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-overlay animate-fade-in" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gk-dialog-title"
        className={cn(
          'relative w-full max-w-form rounded-lg bg-surface p-6 shadow-dialog',
          'animate-dialog-in',
        )}
      >
        <h2 id="gk-dialog-title" className="text-title-sm text-primary">
          {title}
        </h2>
        {description ? <div className="mt-3 text-body-md text-secondary">{description}</div> : null}

        {/* 취소가 좌측이며 기본 포커스를 갖는다. */}
        <div className="mt-6 flex gap-3">
          <Button variant="secondary" size="md" block onClick={onClose} autoFocus>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? 'danger' : 'primary'}
            size="md"
            block
            loading={loading}
            onClick={onConfirm}
            className={destructive ? 'border border-danger' : undefined}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

/** 확인만 필요한 안내형 다이얼로그(이어쓰기 불가 안내 등) */
export function AlertDialog({
  open,
  title,
  description,
  closeLabel = actions.close,
  onClose,
}: {
  open: boolean
  title: string
  description?: ReactNode
  closeLabel?: string
  onClose: () => void
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  useLockBodyScroll(open)
  useFocusTrap(panelRef, open)

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-dialog flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-overlay animate-fade-in" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="gk-alert-title"
        className="relative w-full max-w-form rounded-lg bg-surface p-6 shadow-dialog animate-dialog-in"
      >
        <h2 id="gk-alert-title" className="text-title-sm text-primary">
          {title}
        </h2>
        {description ? <div className="mt-3 text-body-md text-secondary">{description}</div> : null}
        <Button size="md" block className="mt-6" onClick={onClose} autoFocus>
          {closeLabel}
        </Button>
      </div>
    </div>,
    document.body,
  )
}

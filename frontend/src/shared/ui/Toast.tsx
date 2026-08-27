import { useEffect } from 'react'
import { createPortal } from 'react-dom'

import { TOAST_DURATION } from '@/shared/config/constants'
import { cn } from '@/shared/lib/cn'
import { useToastStore } from '@/shared/ui/toastStore'

/**
 * Toast — 디자인 시스템 문서 §8.1
 * 화면 하단(모바일) · 우상단(데스크톱). 정보 4초 · 오류 6초. 동시 1개.
 */
export function ToastViewport() {
  const toast = useToastStore((state) => state.toast)
  const dismiss = useToastStore((state) => state.dismiss)

  useEffect(() => {
    if (!toast) return
    const duration = toast.tone === 'error' ? TOAST_DURATION.error : TOAST_DURATION.info
    const timer = window.setTimeout(dismiss, duration)
    return () => window.clearTimeout(timer)
  }, [toast, dismiss])

  if (!toast) return null

  return createPortal(
    <div
      key={toast.id}
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'fixed z-toast animate-fade-in',
        'bottom-6 left-4 right-4 sm:bottom-auto sm:left-auto sm:right-6 sm:top-6 sm:max-w-sm',
      )}
    >
      <div className="rounded-md bg-action-primary px-4 py-3 text-body-sm text-action-primary-fg shadow-dialog">
        {toast.message}
      </div>
    </div>,
    document.body,
  )
}

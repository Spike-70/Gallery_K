import { type TextareaHTMLAttributes, forwardRef, useCallback, useRef } from 'react'

import { cn } from '@/shared/lib/cn'

/**
 * TextArea — 디자인 시스템 문서 §8.1
 *
 * 최소 행 수를 프롭으로 받고, `autoGrow`면 **내용에 맞춰 늘어난다**(UX §3.13).
 * 500자 테마 원고를 8행 창으로 스크롤하며 쓰게 두면 전체를 볼 수 없다.
 */
export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  invalid?: boolean
  autoGrow?: boolean
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { className, invalid, rows = 8, autoGrow = false, onChange, ...props },
  ref,
) {
  const inner = useRef<HTMLTextAreaElement | null>(null)

  const resize = useCallback((element: HTMLTextAreaElement | null) => {
    if (!element) return
    // 먼저 줄여야 줄어든 내용에도 맞는다. 늘리기만 하면 한 번 커진 창이 돌아오지 않는다.
    element.style.height = 'auto'
    element.style.height = `${element.scrollHeight}px`
  }, [])

  const attach = useCallback(
    (element: HTMLTextAreaElement | null) => {
      inner.current = element
      if (typeof ref === 'function') ref(element)
      else if (ref) ref.current = element
      if (autoGrow) resize(element)
    },
    [ref, autoGrow, resize],
  )

  return (
    <textarea
      ref={attach}
      rows={rows}
      aria-invalid={invalid || undefined}
      onChange={(event) => {
        if (autoGrow) resize(event.currentTarget)
        onChange?.(event)
      }}
      className={cn(
        'w-full rounded-md border bg-surface px-4 py-3 text-body-md text-primary',
        'transition-colors duration-fast ease-standard',
        autoGrow ? 'resize-none overflow-hidden' : 'resize-y',
        invalid ? 'border-danger' : 'border-border-strong',
        className,
      )}
      {...props}
    />
  )
})

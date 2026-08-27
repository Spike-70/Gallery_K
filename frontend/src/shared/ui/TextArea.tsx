import { type TextareaHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'

/** TextArea — 디자인 시스템 문서 §8.1. 최소 행 수를 프롭으로 받는다. */
export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  invalid?: boolean
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { className, invalid, rows = 8, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(
        'w-full resize-y rounded-md border bg-surface px-4 py-3 text-body-md text-primary',
        'transition-colors duration-fast ease-standard',
        invalid ? 'border-danger' : 'border-border-strong',
        className,
      )}
      {...props}
    />
  )
})

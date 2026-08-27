import { type InputHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'

/** DateField — 네이티브 `input[type=date]`을 토큰으로 감싼다(§8.1). */
export type DateFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  invalid?: boolean
}

export const DateField = forwardRef<HTMLInputElement, DateFieldProps>(function DateField(
  { className, invalid, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type="date"
      aria-invalid={invalid || undefined}
      className={cn(
        'h-control-lg w-full rounded-md border bg-surface px-4 text-body-md text-primary',
        invalid ? 'border-danger' : 'border-border-strong',
        className,
      )}
      {...props}
    />
  )
})

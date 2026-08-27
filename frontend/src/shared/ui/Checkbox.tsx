import { type InputHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'
import { Icon } from '@/shared/ui/Icon'

/** Checkbox — 약관 동의 등. 라벨 전체가 히트 영역이며 최소 48px를 확보한다(DS-4). */
export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label: string
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, className, checked, ...props },
  ref,
) {
  return (
    <label className={cn('flex min-h-touch cursor-pointer items-center gap-3', className)}>
      <span className="relative flex h-6 w-6 shrink-0 items-center justify-center">
        <input
          ref={ref}
          type="checkbox"
          checked={checked}
          className={cn(
            'h-6 w-6 appearance-none rounded-sm border bg-surface',
            checked ? 'border-action-primary bg-action-primary' : 'border-border-strong',
          )}
          {...props}
        />
        {checked ? (
          <Icon name="check" size="sm" className="pointer-events-none absolute h-4 w-4 text-inverse" />
        ) : null}
      </span>
      <span className="text-body-md text-primary">{label}</span>
    </label>
  )
})

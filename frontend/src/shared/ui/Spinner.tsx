import { cn } from '@/shared/lib/cn'

/** 스피너 — 디자인 시스템 문서 §8.1. 20/24/32px, 1.1초 회전. */
const SIZE_CLASS = {
  sm: 'h-5 w-5 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-3',
} as const

export type SpinnerProps = {
  ref?: React.Ref<HTMLSpanElement>
  size?: keyof typeof SIZE_CLASS
  className?: string
  label?: string
}

export function Spinner({ size = 'sm', className, label, ref }: SpinnerProps) {
  return (
    <span
      ref={ref}
      className={cn(
        'inline-block animate-spin rounded-full border-border-strong border-t-transparent',
        SIZE_CLASS[size],
        className,
      )}
      role={label ? 'status' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    />
  )
}

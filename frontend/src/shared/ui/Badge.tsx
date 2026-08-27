import { cn } from '@/shared/lib/cn'

/** Badge — 정보성 표식. `neutral`/`accent` 2종(디자인 시스템 문서 §8.1). */
export type BadgeProps = {
  ref?: React.Ref<HTMLSpanElement>
  children: string
  tone?: 'neutral' | 'accent'
  className?: string
}

export function Badge({ children, tone = 'neutral', className, ref }: BadgeProps) {
  return (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-sm px-2 py-px text-label',
        tone === 'neutral' ? 'bg-subtle text-secondary' : 'bg-accent-subtle text-accent',
        className,
      )}
    >
      {children}
    </span>
  )
}

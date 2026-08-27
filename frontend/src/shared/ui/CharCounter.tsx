import { cn } from '@/shared/lib/cn'
import { templates } from '@/shared/config/messages'

/**
 * CharCounter — 디자인 시스템 문서 §8.1
 * `현재/최대` 형식. 초과 시 숫자만 danger 색으로 바꾸고 **입력은 막지 않는다**(PRD §6.10).
 */
export type CharCounterProps = {
  current: number
  max: number
  className?: string
}

export function CharCounter({ current, max, className }: CharCounterProps) {
  const exceeded = current > max
  return (
    <span
      className={cn('tabular text-caption', exceeded ? 'text-danger' : 'text-tertiary', className)}
      aria-live="polite"
    >
      {templates.charCounter(current, max)}
    </span>
  )
}

import { cn } from '@/shared/lib/cn'

/** PositionIndicator — `3 / 12`. 서버가 완성한 문자열을 그대로 출력한다(§8.2). */
export function PositionIndicator({ label, className }: { label: string; className?: string }) {
  return <p className={cn('tabular text-center text-caption text-tertiary', className)}>{label}</p>
}

import { cn } from '@/shared/lib/cn'

/**
 * ProgressRing — 업로드 진행률(디자인 시스템 문서 §8.1)
 * 값이 없으면 무한 회전한다.
 */
export type ProgressRingProps = {
  ref?: React.Ref<SVGSVGElement>
  /** 0–100. `null`이면 불확정 상태 */
  value: number | null
  size?: 'sm' | 'md'
  className?: string
  label?: string
}

const DIMENSION = { sm: 24, md: 40 } as const

export function ProgressRing({ value, size = 'sm', className, label, ref }: ProgressRingProps) {
  const dimension = DIMENSION[size]
  const radius = dimension / 2 - 2
  const circumference = 2 * Math.PI * radius
  const clamped = value === null ? 25 : Math.min(100, Math.max(0, value))
  const dash = (clamped / 100) * circumference

  return (
    <svg
      ref={ref}
      width={dimension}
      height={dimension}
      viewBox={`0 0 ${dimension} ${dimension}`}
      className={cn(value === null && 'animate-spin', className)}
      role={label ? 'progressbar' : undefined}
      aria-label={label}
      aria-valuenow={value ?? undefined}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <circle
        cx={dimension / 2}
        cy={dimension / 2}
        r={radius}
        fill="none"
        stroke="var(--gk-border-default)"
        strokeWidth="2"
      />
      <circle
        cx={dimension / 2}
        cy={dimension / 2}
        r={radius}
        fill="none"
        stroke="var(--gk-text-accent)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circumference}`}
        transform={`rotate(-90 ${dimension / 2} ${dimension / 2})`}
      />
    </svg>
  )
}

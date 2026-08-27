import { cn } from '@/shared/lib/cn'

/**
 * Skeleton — 디자인 시스템 문서 §8.1
 * **썸네일 스켈레톤은 LQIP가 있으면 쓰지 않는다** — 블러 이미지가 더 나은 플레이스홀더다.
 */
export type SkeletonProps = {
  className?: string
  /** 여러 줄 텍스트 자리를 잡을 때 */
  lines?: number
}

export function Skeleton({ className, lines }: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div className="flex flex-col gap-2" aria-hidden>
        {Array.from({ length: lines }, (_, index) => (
          <div
            key={index}
            className={cn('gk-shimmer h-4 rounded-sm', index === lines - 1 && 'w-2/3', className)}
          />
        ))}
      </div>
    )
  }
  return <div aria-hidden className={cn('gk-shimmer rounded-sm', className)} />
}

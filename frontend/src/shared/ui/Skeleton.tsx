import { cn } from '@/shared/lib/cn'

/**
 * Skeleton — 디자인 시스템 문서 §8.1
 * **썸네일 스켈레톤은 LQIP가 있으면 쓰지 않는다** — 블러 이미지가 더 나은 플레이스홀더다.
 */
export type SkeletonProps = {
  ref?: React.Ref<HTMLDivElement>
  className?: string
  /** 여러 줄 텍스트 자리를 잡을 때 */
  lines?: number
}

export function Skeleton({ className, lines, ref }: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div
        ref={ref} className="flex flex-col gap-2" aria-hidden>
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

/**
 * 화면 하나가 통째로 준비되지 않았을 때의 자리 — 라우트 전환·세션 부팅.
 *
 * **전체 화면 스피너를 쓰지 않는다**(디자인 시스템 §10 금지 항목). 스피너는 "기다려라"만
 * 말하지만 스켈레톤은 곧 무엇이 올지 말한다. 흰 화면도 만들지 않는다(UX §10).
 */
export function ScreenSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-label={label} className="gk-container-gallery flex flex-col gap-4 py-16">
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-4 w-full" lines={3} />
      <Skeleton className="h-block w-full" />
    </div>
  )
}

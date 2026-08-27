import { cn } from '@/shared/lib/cn'

/**
 * ExhibitionTitle — 제목 + 연장 라벨(디자인 시스템 문서 §8.2)
 *
 * 연장 라벨은 서버가 완성해 준 문구(`8월 30일의 전시`)를 그대로 쓴다.
 * **사과 문구를 붙이지 않는다**(UX-4).
 */
export type ExhibitionTitleProps = {
  title: string
  carriedOverLabel?: string | null
  as?: 'h1' | 'h2'
  className?: string
}

export function ExhibitionTitle({ title, carriedOverLabel, as = 'h1', className }: ExhibitionTitleProps) {
  const Heading = as
  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <Heading className="text-center text-title-lg text-primary">{title}</Heading>
      {carriedOverLabel ? <p className="text-caption text-tertiary">{carriedOverLabel}</p> : null}
    </div>
  )
}

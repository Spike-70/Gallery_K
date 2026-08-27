import { cn } from '@/shared/lib/cn'
import type { ExhibitionDayStatus } from '@/shared/types/enums'
import { Icon } from '@/shared/ui/Icon'

/**
 * StatusChip — 발행 상태(디자인 시스템 문서 §8.3)
 *
 * **문자 · 색 · 아이콘의 3중 표기**다(DS-5). 스캔 속도가 관리자 홈의 전부이므로
 * 색만 바꾸는 표기를 쓰지 않는다.
 *
 * 도메인 열거형(`ExhibitionDayStatus`)을 프롭으로 받지만, 이 값은 서버 열거형의
 * 미러이며 `shared/types/enums`에 있다. 도메인 객체를 받지는 않는다(프런트 §4.3).
 */
export type StatusChipProps = {
  status: ExhibitionDayStatus
  /** `carried_over`일 때 `↑ 08.30`의 날짜 부분 */
  carriedFromLabel?: string | null
  className?: string
}

export function StatusChip({ status, carriedFromLabel, className }: StatusChipProps) {
  if (status === 'published') {
    return (
      <span className={cn('inline-flex items-center gap-1 text-label text-published', className)}>
        <Icon name="check" size="sm" className="h-4 w-4" />Y
      </span>
    )
  }

  if (status === 'empty') {
    return (
      <span className={cn('inline-flex items-center gap-1 text-label text-empty', className)}>
        <span aria-hidden className="h-2 w-2 rounded-full bg-empty" />N
      </span>
    )
  }

  return (
    <span className={cn('inline-flex items-center gap-1 text-label text-carried', className)}>
      <Icon name="arrow-up" size="sm" className="h-4 w-4" />
      {carriedFromLabel ?? ''}
    </span>
  )
}

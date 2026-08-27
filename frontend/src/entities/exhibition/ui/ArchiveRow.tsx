import { Link } from 'react-router-dom'

import { ArtworkImage } from '@/entities/artwork/ui/ArtworkImage'
import type { ExhibitionSummary } from '@/entities/exhibition/model/types'
import { cn } from '@/shared/lib/cn'
import { formatArchiveDate } from '@/shared/lib/date'

/**
 * ArchiveRow — 디자인 시스템 문서 §8.2
 *
 * 행 높이 최소 72px. **감상 표식을 배지로 두지 않는다** — 본 전시의 제목 색을
 * 낮추는 것으로만 구분한다(UX-3, U-3). `NEW`·미열람 카운트는 존재하지 않는다.
 */
export type ArchiveRowProps = {
  exhibition: ExhibitionSummary
  to: string
}

export function ArchiveRow({ exhibition, to }: ArchiveRowProps) {
  return (
    <Link
      to={to}
      className="flex min-h-row items-center gap-4 border-b border-border-default py-3"
    >
      <div className="h-16 w-16 shrink-0 overflow-hidden">
        <ArtworkImage image={exhibition.coverImage} alt="" variant="thumb" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-caption text-tertiary">{formatArchiveDate(exhibition.date)}</span>
        <span
          className={cn(
            'truncate text-title-sm',
            exhibition.isViewed ? 'text-tertiary' : 'text-primary',
          )}
        >
          {exhibition.title}
        </span>
      </div>
    </Link>
  )
}

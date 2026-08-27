import { Link } from 'react-router-dom'

import { DateLine } from '@/entities/exhibition/ui/DateLine'
import { ExhibitionTitle } from '@/entities/exhibition/ui/ExhibitionTitle'
import { formatFullDate } from '@/shared/lib/date'
import type { IsoDate } from '@/shared/types/utility'

/**
 * 전시 머리말 — 디자인 시스템 문서 §4.2 대응(화면 전용 조합)
 *
 * `DateLine` + `ExhibitionTitle` + 연장 라벨의 조합이며, 이름에 문맥을 담아
 * 도메인 표현 컴포넌트와 구분한다(프런트 §4.2).
 *
 * 날짜는 **관람일**을 보여준다. 전시 발행일이 아니다(UX §3.6).
 */
export type ExhibitionHeaderProps = {
  viewingDate: IsoDate
  title: string
  carriedOverLabel: string | null
  /** 제목을 탭하면 전시 테마(C-1)로 간다 */
  themeTo: string
}

export function ExhibitionHeader({ viewingDate, title, carriedOverLabel, themeTo }: ExhibitionHeaderProps) {
  return (
    <header className="flex flex-col items-center gap-2 pb-6">
      <DateLine label={formatFullDate(viewingDate)} />
      <Link to={themeTo} className="min-h-touch">
        <ExhibitionTitle title={title} carriedOverLabel={carriedOverLabel} />
      </Link>
    </header>
  )
}

import { Link } from 'react-router-dom'

import type { AdminExhibitionDay } from '@/entities/exhibition/model/admin'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { actions, screens, templates } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { cn } from '@/shared/lib/cn'
import { formatShortDate } from '@/shared/lib/date'
import { Button, LinkButton, StatusChip } from '@/shared/ui'

/**
 * 날짜 행 — 디자인 시스템 문서 §8.3, UX 설계서 §3.11
 *
 * **3열 고정**이다. 스캔 속도가 이 화면의 전부이므로 열이 흔들리지 않아야 한다.
 * 오늘 행은 좌측에 2px accent 바를 붙인다.
 *
 * 2열 버튼의 4가지 모습은 서버가 준 `editMode`가 결정한다. 프런트가 날짜를 비교하지 않는다.
 */
export type DayRowProps = {
  day: AdminExhibitionDay
  onCarryDraft: (day: AdminExhibitionDay) => void
}

export function DayRow({ day, onCarryDraft }: DayRowProps) {
  const dateLabel = day.isToday ? `${screens.admin.today} · ${formatShortDate(day.date)}` : formatShortDate(day.date)
  const carriedLabel = day.carriedFromDate ? formatShortDate(day.carriedFromDate).slice(0, 5) : null

  return (
    <li
      className={cn(
        'grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border-default py-3 pl-3',
        day.isToday && 'border-l-2 border-l-accent',
      )}
    >
      <div className="flex flex-col">
        <span className="tabular text-body-md text-primary">{dateLabel}</span>
        {day.title ? <span className="truncate text-caption text-tertiary">{day.title}</span> : null}
      </div>

      <div className="flex justify-end">
        {day.editMode === 'create' ? (
          <LinkButton to={paths.adminExhibition(day.date)} size="sm" variant="secondary">
            {actions.publishUp}
          </LinkButton>
        ) : day.editMode === 'edit' ? (
          <Link
            to={paths.adminExhibition(day.date)}
            className="inline-flex min-h-touch items-center px-2 text-body-sm text-accent underline underline-offset-4"
          >
            {actions.edit}
          </Link>
        ) : day.editMode === 'carry_draft' ? (
          <Button size="sm" variant="secondary" onClick={() => onCarryDraft(day)}>
            {actions.carryDraft}
          </Button>
        ) : (
          <span aria-hidden className="px-2 text-body-sm text-tertiary">
            —
          </span>
        )}
      </div>

      <div className="flex min-w-row flex-col items-end gap-1">
        <StatusChip status={day.status} carriedFromLabel={carriedLabel} />
        {/* 진행률은 `N`이고 드래프트가 있을 때만. 주말에 미리 채워둔 상황이 한눈에 보인다. */}
        {day.status === 'empty' && day.hasDraft ? (
          <span className="tabular text-caption text-tertiary">
            {templates.draftProgress(day.draftProgress.completeArtworkCount, ARTWORK_COUNT)}
          </span>
        ) : null}
      </div>
    </li>
  )
}

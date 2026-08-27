import { Link } from 'react-router-dom'

import type { Notice } from '@/entities/notice/model/types'
import { actions } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'

/**
 * NoticeBanner — 휴관 공지(디자인 시스템 문서 §8.2)
 * **경계선만 쓰고 배경색을 두지 않는다.** 경고처럼 보이지 않게 한다(UX-4).
 */
export type NoticeBannerProps = {
  notice: Notice
  archiveTo: string
  className?: string
}

export function NoticeBanner({ notice, archiveTo, className }: NoticeBannerProps) {
  return (
    <div className={cn('rounded-md border border-border-default p-4 text-center', className)}>
      <p className="text-body-sm text-secondary">{notice.body}</p>
      <Link to={archiveTo} className="mt-2 inline-flex min-h-touch items-center text-body-sm text-accent underline underline-offset-4">
        {actions.viewPastExhibitions}
      </Link>
    </div>
  )
}

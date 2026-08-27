import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Icon, type IconName } from '@/shared/ui/Icon'

/**
 * Banner — 화면 상단 고정 안내(디자인 시스템 문서 §8.1)
 *
 * `info`(지난 전시 보는 중) / `offline`(연결 없음) / `update`(새 버전).
 * **경고색을 쓰지 않는다** — 사용자의 잘못이 아니다(UX-4).
 */
export type BannerProps = {
  ref?: React.Ref<HTMLDivElement>
  tone?: 'info' | 'offline' | 'update'
  message: string
  /** 우측 동작(`오늘의 전시로`, `새로고침` 등) */
  action?: ReactNode
  className?: string
}

const TONE_ICON: Record<NonNullable<BannerProps['tone']>, IconName> = {
  info: 'info',
  offline: 'info',
  update: 'refresh',
}

export function Banner({ tone = 'info', message, action, className, ref }: BannerProps) {
  return (
    <div
      ref={ref}
      role="status"
      className={cn(
        'flex w-full items-center justify-between gap-3 border-b border-border-default bg-surface px-4 py-3',
        className,
      )}
    >
      <span className="flex items-center gap-2 text-body-sm text-secondary">
        <Icon name={TONE_ICON[tone]} size="sm" className="text-tertiary" />
        {message}
      </span>
      {action}
    </div>
  )
}

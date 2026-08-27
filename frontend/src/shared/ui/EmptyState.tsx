import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Icon, type IconName } from '@/shared/ui/Icon'

/**
 * EmptyState — 아이콘 + 한 줄 문구 + 선택적 동작(§8.1)
 * **일러스트레이션을 쓰지 않는다.** 한 줄 문구와 다음 행동 하나면 충분하다(UX §11).
 */
export type EmptyStateProps = {
  ref?: React.Ref<HTMLDivElement>
  message: string
  icon?: IconName
  action?: ReactNode
  className?: string
}

export function EmptyState({ message, icon = 'image', action, className, ref }: EmptyStateProps) {
  return (
    <div
      ref={ref} className={cn('flex flex-col items-center gap-4 px-4 py-12 text-center', className)}>
      <Icon name={icon} size="lg" className="text-tertiary" />
      <p className="text-body-md text-secondary">{message}</p>
      {action}
    </div>
  )
}

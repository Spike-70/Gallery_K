import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

/**
 * 폼 상단 배너 — 프런트엔드 아키텍처 문서 §7.2
 *
 * `field_errors`가 없는 폼 오류는 여기에 표시한다. 문구는 서버 응답을 그대로 쓴다.
 * `info`는 오류가 아닌 안내다(재설정 완료 등) — **경고색을 쓰지 않는다**(UX-4).
 *
 * `action`은 **막다른 오류에 길을 하나 여는 자리**다. 예를 들어 A-4에서 "이미 가입된
 * 번호입니다"가 뜨면, 그 사람이 지금 해야 할 일은 연결 모드로 옮겨 가는 것이다.
 */
export type FormBannerProps = {
  message: string
  tone?: 'error' | 'info'
  action?: ReactNode
  className?: string
}

export function FormBanner({ message, tone = 'error', action, className }: FormBannerProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'flex flex-col gap-1 rounded-md border px-4 py-3 text-body-sm',
        tone === 'error'
          ? 'border-danger bg-danger-subtle text-danger'
          : 'border-border-default bg-surface text-secondary',
        className,
      )}
    >
      <p className="m-0">{message}</p>
      {action}
    </div>
  )
}

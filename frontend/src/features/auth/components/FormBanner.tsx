import { cn } from '@/shared/lib/cn'

/**
 * 폼 상단 배너 — 프런트엔드 아키텍처 문서 §7.2
 *
 * `field_errors`가 없는 폼 오류는 여기에 표시한다. 문구는 서버 응답을 그대로 쓴다.
 * `info`는 오류가 아닌 안내다(재설정 완료 등) — **경고색을 쓰지 않는다**(UX-4).
 */
export type FormBannerProps = {
  message: string
  tone?: 'error' | 'info'
  className?: string
}

export function FormBanner({ message, tone = 'error', className }: FormBannerProps) {
  return (
    <p
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'rounded-md border px-4 py-3 text-body-sm',
        tone === 'error'
          ? 'border-danger bg-danger-subtle text-danger'
          : 'border-border-default bg-surface text-secondary',
        className,
      )}
    >
      {message}
    </p>
  )
}

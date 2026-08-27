import { cn } from '@/shared/lib/cn'
import { actions, screens } from '@/shared/config/messages'
import { Button } from '@/shared/ui/Button'

/**
 * ErrorState — 문구 + 재시도(§8.1)
 * **부분 실패에는 화면 전체를 대체하지 않는다.** 실패한 영역만 이 컴포넌트로 바꾼다.
 * 기술 정보를 노출하지 않으며 `requestId`만 `문의 번호`로 병기한다(UX §3.19).
 */
export type ErrorStateProps = {
  ref?: React.Ref<HTMLDivElement>
  message: string
  onRetry?: () => void
  retryLabel?: string
  requestId?: string | null
  size?: 'inline' | 'page'
  className?: string
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = actions.retry,
  requestId,
  size = 'page',
  className,
  ref,
}: ErrorStateProps) {
  return (
    <div
      ref={ref}
      role="alert"
      className={cn(
        'flex flex-col items-center gap-4 text-center',
        size === 'page' ? 'px-4 py-16' : 'px-4 py-8',
        className,
      )}
    >
      <p className="text-body-md text-primary">{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="md" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
      {requestId ? (
        <p className="text-caption text-tertiary">
          {screens.errors.requestIdLabel} {requestId}
        </p>
      ) : null}
    </div>
  )
}

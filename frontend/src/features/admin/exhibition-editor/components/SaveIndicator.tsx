import { status } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Spinner, TextButton } from '@/shared/ui'

/**
 * SaveIndicator — 디자인 시스템 문서 §8.3
 *
 * **3상태 외에 없다.** `저장 중…` / `저장됨 · 방금` / `저장 실패 · 다시 시도`.
 * 자동 저장은 낙관적이지 않다. 진행 상태를 명시한다(프런트 §6.4).
 */
export type SaveState = 'idle' | 'saving' | 'saved' | 'failed'

export type SaveIndicatorProps = {
  state: SaveState
  onRetry?: () => void
  className?: string
}

export function SaveIndicator({ state, onRetry, className }: SaveIndicatorProps) {
  if (state === 'idle') return <span className={cn('text-caption text-tertiary', className)} />

  if (state === 'saving') {
    return (
      <span className={cn('flex items-center gap-2 text-caption text-tertiary', className)} aria-live="polite">
        <Spinner size="sm" className="h-4 w-4" />
        {status.saving}
      </span>
    )
  }

  if (state === 'saved') {
    return (
      <span className={cn('text-caption text-tertiary', className)} aria-live="polite">
        {status.saved}
      </span>
    )
  }

  /**
   * `저장 실패 · 다시 시도`가 **문구이자 동작**이다. 옆에 재시도 버튼을 또 두면
   * "다시 시도"가 두 번 나온다. 표시 전체를 누를 수 있게 만들어 3상태 계약을 지킨다.
   */
  if (!onRetry) {
    return (
      <span className={cn('text-caption text-danger', className)} role="alert">
        {status.saveFailed}
      </span>
    )
  }

  return (
    <span role="alert" className={cn('inline-flex', className)}>
      <TextButton tone="danger" className="text-caption" onClick={onRetry}>
        {status.saveFailed}
      </TextButton>
    </span>
  )
}

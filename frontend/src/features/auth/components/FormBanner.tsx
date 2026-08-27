import { cn } from '@/shared/lib/cn'

/**
 * 폼 상단 배너 — 프런트엔드 아키텍처 문서 §7.2
 * `field_errors`가 없는 폼 오류는 여기에 표시한다. 문구는 서버 응답을 그대로 쓴다.
 */
export function FormBanner({ message, className }: { message: string; className?: string }) {
  return (
    <p
      role="alert"
      className={cn('rounded-md border border-danger bg-danger-subtle px-4 py-3 text-body-sm text-danger', className)}
    >
      {message}
    </p>
  )
}

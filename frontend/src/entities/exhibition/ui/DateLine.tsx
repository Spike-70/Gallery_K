import { cn } from '@/shared/lib/cn'

/**
 * DateLine — `2026. 08. 27. 목` (디자인 시스템 문서 §8.2)
 * **서버가 준 문자열을 그대로 출력한다.** 요일 로케일 처리를 클라이언트에 분산시키지 않는다.
 */
export function DateLine({ label, className }: { label: string; className?: string }) {
  return <p className={cn('text-center text-caption text-tertiary', className)}>{label}</p>
}

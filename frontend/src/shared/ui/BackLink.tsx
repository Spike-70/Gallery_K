import { cn } from '@/shared/lib/cn'
import { TextLink } from '@/shared/ui/TextLink'

/**
 * BackLink — **모든 화면 하단의 필수 요소**(UX-3, 디자인 시스템 S-4)
 *
 * 시니어 사용자는 브라우저 뒤로가기도, 상단 아이콘도 쓰지 않는다(PRD §5.2).
 * 하단 텍스트 링크가 1급이며 상단 `←`는 보조 수단이다.
 *
 * 되돌아갈 대상은 **페이지가 명시적으로 지정**한다. 하위 컴포넌트가
 * `history.back()`을 호출하지 않는다(프런트 §8.1).
 */
export type BackLinkProps = {
  to: string
  label: string
  className?: string
}

export function BackLink({ to, label, className }: BackLinkProps) {
  return (
    <nav className={cn('flex justify-center py-8', className)} aria-label="되돌아가기">
      <TextLink to={to}>{label}</TextLink>
    </nav>
  )
}

/** 되돌아갈 곳이 둘인 화면(지난 전시 상세)에서 쓴다. */
export function BackLinkGroup({
  links,
  className,
}: {
  links: BackLinkProps[]
  className?: string
}) {
  return (
    <nav className={cn('flex flex-col items-center gap-2 py-8', className)} aria-label="되돌아가기">
      {links.map((link) => (
        <TextLink key={link.to + link.label} to={link.to}>
          {link.label}
        </TextLink>
      ))}
    </nav>
  )
}

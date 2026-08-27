import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

import { cn } from '@/shared/lib/cn'

/**
 * TextLink — 디자인 시스템 문서 §8.1
 * **밑줄을 상시 표시**한다. 색만으로 구분하지 않는다(DS-5).
 * 하단 되돌아가기 링크의 기본형이며 히트 영역은 48px를 확보한다.
 */
const linkClass = (tone: 'default' | 'accent' | 'danger' | 'tertiary', className?: string) =>
  cn(
    'inline-flex min-h-touch items-center justify-center gap-1 underline underline-offset-4',
    'text-body-md transition-colors duration-fast ease-standard',
    tone === 'default' && 'text-primary hover:text-accent',
    tone === 'accent' && 'text-accent hover:text-primary',
    tone === 'tertiary' && 'text-tertiary hover:text-secondary',
    tone === 'danger' && 'text-danger',
    className,
  )

export type TextLinkTone = 'default' | 'accent' | 'danger' | 'tertiary'

export type TextLinkProps = LinkProps & { tone?: TextLinkTone }

export const TextLink = forwardRef<HTMLAnchorElement, TextLinkProps>(function TextLink(
  { tone = 'default', className, ...props },
  ref,
) {
  return <Link ref={ref} className={linkClass(tone, className)} {...props} />
})

/** 라우터를 거치지 않는 동작(모달 열기 등)에 쓰는 버튼형 링크 */
export type TextButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type'> & {
  tone?: TextLinkTone
  onClick?: () => void
}

export function TextButton({ tone = 'default', className, onClick, children, ...props }: TextButtonProps) {
  return (
    <button type="button" className={linkClass(tone, className)} onClick={onClick} {...props}>
      {children}
    </button>
  )
}

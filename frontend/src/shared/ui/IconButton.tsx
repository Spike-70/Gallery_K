import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { Link } from 'react-router-dom'

import { cn } from '@/shared/lib/cn'
import { Icon, type IconName } from '@/shared/ui/Icon'

/**
 * IconButton — 48×48px 고정. `label`(= `aria-label`)이 필수다(§8.1).
 *
 * `as="link"`는 이동을 뜻한다. 이동을 `button` + `navigate()`로 만들면 새 탭 열기·
 * 링크 복사가 사라지고, 스크린리더가 "버튼"이라고 잘못 읽는다.
 */
const iconButtonClass = (tone: 'default' | 'inverse', className?: string) =>
  cn(
    'inline-flex h-touch w-touch items-center justify-center rounded-md',
    'transition-colors duration-fast ease-standard',
    tone === 'default' ? 'text-primary hover:bg-subtle' : 'text-inverse hover:bg-overlay',
    className,
  )

type IconButtonBase = {
  icon: IconName
  label: string
  iconSize?: 'sm' | 'md' | 'lg'
  tone?: 'default' | 'inverse'
  className?: string
}

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  IconButtonBase & { as?: 'button' }

export type IconLinkProps = IconButtonBase & { as: 'link'; to: string }

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps | IconLinkProps>(
  function IconButton(props, ref) {
    const { icon, label, iconSize = 'md', tone = 'default', className } = props

    if (props.as === 'link') {
      return (
        <Link to={props.to} aria-label={label} className={iconButtonClass(tone, className)}>
          <Icon name={icon} size={iconSize} />
        </Link>
      )
    }

    const { as: _as, icon: _icon, label: _label, iconSize: _iconSize, tone: _tone, className: _className, type, ...rest } = props
    return (
      <button ref={ref} type={type ?? 'button'} aria-label={label} className={iconButtonClass(tone, className)} {...rest}>
        <Icon name={icon} size={iconSize} />
      </button>
    )
  },
)

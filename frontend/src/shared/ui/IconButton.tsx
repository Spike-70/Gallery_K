import { type ButtonHTMLAttributes, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'
import { Icon, type IconName } from '@/shared/ui/Icon'

/** IconButton — 48×48px 고정. `label`(= `aria-label`)이 필수다(§8.1). */
export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: IconName
  label: string
  iconSize?: 'sm' | 'md' | 'lg'
  tone?: 'default' | 'inverse'
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, label, iconSize = 'md', tone = 'default', className, type, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      aria-label={label}
      className={cn(
        'inline-flex h-touch w-touch items-center justify-center rounded-md',
        'transition-colors duration-fast ease-standard',
        tone === 'default' ? 'text-primary hover:bg-subtle' : 'text-inverse hover:bg-overlay',
        className,
      )}
      {...props}
    >
      <Icon name={icon} size={iconSize} />
    </button>
  )
})

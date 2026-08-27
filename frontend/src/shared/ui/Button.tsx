import { type VariantProps, cva } from 'class-variance-authority'
import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'
import { Spinner } from '@/shared/ui/Spinner'

/**
 * Button — 디자인 시스템 문서 §8.1
 *
 * - `loading` 상태에서 **라벨을 유지**한다. 라벨이 사라지면 시니어 사용자가
 *   무엇을 눌렀는지 잃는다.
 * - `disabled`는 `aria-disabled`로 표기하고 포커스를 유지한다(이유를 읽을 수 있어야 한다).
 * - `size=sm`의 히트 영역은 의사요소로 48px까지 확장한다(DS-4).
 */
export const buttonVariants = cva(
  [
    'relative inline-flex items-center justify-center gap-2 rounded-md',
    'font-sans text-body-md text-center',
    'transition-colors duration-fast ease-standard',
    'aria-disabled:cursor-not-allowed aria-disabled:opacity-40',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-action-primary text-action-primary-fg hover:bg-action-primary-hover',
        secondary: 'border border-border-strong bg-surface text-primary hover:bg-subtle',
        ghost: 'text-primary hover:bg-subtle',
        danger: 'text-danger hover:bg-danger-subtle',
      },
      size: {
        lg: 'h-control-lg px-6',
        md: 'h-control-md px-5',
        sm: 'gk-hit-expand h-control-sm px-4 text-body-sm',
      },
      block: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: { variant: 'primary', size: 'lg', block: false },
  },
)

export type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'disabled'> &
  VariantProps<typeof buttonVariants> & {
    loading?: boolean
    disabled?: boolean
    /** 라벨 앞 아이콘 등 */
    leading?: ReactNode
  }

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant,
    size,
    block,
    loading = false,
    disabled = false,
    leading,
    children,
    type,
    onClick,
    ...props
  },
  ref,
) {
  const inactive = disabled || loading
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={cn(buttonVariants({ variant, size, block }), className)}
      aria-disabled={inactive || undefined}
      aria-busy={loading || undefined}
      {...props}
      onClick={inactive ? undefined : onClick}
    >
      {loading ? <Spinner size="sm" className="border-current border-t-transparent" /> : leading}
      <span>{children}</span>
    </button>
  )
})

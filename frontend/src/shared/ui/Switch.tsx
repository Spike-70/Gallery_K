import { cn } from '@/shared/lib/cn'

/**
 * Switch — 디자인 시스템 문서 §8.1
 * 48×28px 트랙. 라벨을 좌측에 두고 **라벨 전체가 히트 영역**이다.
 */
export type SwitchProps = {
  ref?: React.Ref<HTMLButtonElement>
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label: string
  description?: string
  disabled?: boolean
  className?: string
}

export function Switch({ checked, onCheckedChange, label, description, disabled, className, ref }: SwitchProps) {
  return (
    <button
      ref={ref}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled || undefined}
      onClick={disabled ? undefined : () => onCheckedChange(!checked)}
      className={cn(
        'flex min-h-touch w-full items-center justify-between gap-4 rounded-md px-1 text-left',
        'transition-colors duration-fast ease-standard',
        disabled ? 'cursor-not-allowed opacity-50' : 'hover:bg-subtle',
        className,
      )}
    >
      <span className="flex flex-col">
        <span className="text-body-md text-primary">{label}</span>
        {description ? <span className="text-caption text-tertiary">{description}</span> : null}
      </span>

      <span
        aria-hidden
        className={cn(
          'relative h-switch-track w-12 shrink-0 rounded-full transition-colors duration-fast ease-standard',
          checked ? 'bg-action-primary' : 'bg-border-strong',
        )}
      >
        <span
          className={cn(
            'absolute top-1 h-5 w-5 rounded-full bg-surface transition-transform duration-fast ease-standard',
            checked ? 'translate-x-6' : 'translate-x-1',
          )}
        />
      </span>
    </button>
  )
}

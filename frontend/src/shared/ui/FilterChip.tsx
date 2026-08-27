import { cn } from '@/shared/lib/cn'
import { Icon } from '@/shared/ui/Icon'

/** FilterChip — 목록 필터 토글(§8.1). 선택 시 accent 배경 + 체크. 히트 영역 48px. */
export type FilterChipProps = {
  ref?: React.Ref<HTMLButtonElement>
  label: string
  selected: boolean
  onSelect: () => void
}

export function FilterChip({ label, selected, onSelect, ref }: FilterChipProps) {
  return (
    <button
      ref={ref}
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        'inline-flex min-h-touch items-center gap-1 rounded-sm border px-4 text-body-sm',
        'transition-colors duration-fast ease-standard',
        selected
          ? 'border-accent bg-accent-subtle text-accent'
          : 'border-border-default bg-surface text-secondary hover:bg-subtle',
      )}
    >
      {selected ? <Icon name="check" size="sm" className="h-4 w-4" /> : null}
      {label}
    </button>
  )
}

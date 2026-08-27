import { BottomSheet } from '@/shared/ui/BottomSheet'
import { Icon } from '@/shared/ui/Icon'
import { cn } from '@/shared/lib/cn'

/**
 * TimeSelectSheet — 시각 선택 바텀시트(디자인 시스템 문서 §8.1)
 *
 * **드럼이 아닌 목록 선택**으로 구현한다 — 드럼은 시니어에게 조작이 어렵다(S-10).
 */
export type TimeSelectSheetProps = {
  open: boolean
  title: string
  value: string
  options: string[]
  onSelect: (value: string) => void
  onClose: () => void
}

export function TimeSelectSheet({ open, title, value, options, onSelect, onClose }: TimeSelectSheetProps) {
  return (
    <BottomSheet open={open} title={title} onClose={onClose}>
      <ul className="flex flex-col">
        {options.map((option) => {
          const selected = option === value
          return (
            <li key={option}>
              <button
                type="button"
                aria-current={selected || undefined}
                onClick={() => {
                  onSelect(option)
                  onClose()
                }}
                className={cn(
                  'flex h-touch w-full items-center justify-between rounded-md px-3 text-body-md',
                  'transition-colors duration-fast ease-standard hover:bg-subtle',
                  selected ? 'text-accent' : 'text-primary',
                )}
              >
                <span className="tabular">{option}</span>
                {selected ? <Icon name="check" size="sm" /> : null}
              </button>
            </li>
          )
        })}
      </ul>
    </BottomSheet>
  )
}

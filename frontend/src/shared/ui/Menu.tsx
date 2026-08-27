import { useEffect, useRef, useState } from 'react'

import { cn } from '@/shared/lib/cn'
import { IconButton } from '@/shared/ui/IconButton'

/**
 * Menu — `⋯` 버튼이 여는 액션 목록(디자인 시스템 문서 §8.1)
 * 항목 높이 48px. **파괴적 항목은 `danger` + 최하단**이다(UX-6).
 */
export type MenuItem = {
  label: string
  onSelect: () => void
  destructive?: boolean
}

export type MenuProps = {
  ref?: React.Ref<HTMLDivElement>
  label: string
  items: MenuItem[]
}

export function Menu({ label, items, ref }: MenuProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  // 파괴적 항목을 항상 최하단으로 내린다. 사용처가 순서를 잊어도 규칙이 지켜진다.
  const ordered = [...items].sort((a, b) => Number(a.destructive ?? false) - Number(b.destructive ?? false))

  return (
    <div
      ref={(node) => {
        // 바깥 클릭 감지를 위한 내부 ref 와 사용처가 준 ref 를 함께 채운다.
        containerRef.current = node
        if (typeof ref === 'function') ref(node)
        else if (ref) ref.current = node
      }}
      className="relative"
    >
      <IconButton icon="more" label={label} aria-expanded={open} onClick={() => setOpen((v) => !v)} />
      {open ? (
        <ul
          role="menu"
          className="absolute right-0 top-full z-dialog min-w-block overflow-hidden rounded-md border border-border-default bg-surface shadow-dialog"
        >
          {ordered.map((item) => (
            <li key={item.label} role="none">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false)
                  item.onSelect()
                }}
                className={cn(
                  'flex h-touch w-full items-center px-4 text-left text-body-sm',
                  'transition-colors duration-fast ease-standard hover:bg-subtle',
                  item.destructive ? 'text-danger' : 'text-primary',
                )}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

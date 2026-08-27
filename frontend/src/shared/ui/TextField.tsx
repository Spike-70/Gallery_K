import { type InputHTMLAttributes, type ReactNode, forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'

/**
 * TextField — 디자인 시스템 문서 §8.1
 * 라벨은 `FieldGroup`이 소유한다. 이 컴포넌트는 입력 표면만 책임진다.
 */
export type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean
  fieldSize?: 'md' | 'lg'
  /** 우측 부속(비밀번호 보기 토글 등) */
  trailing?: ReactNode
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { className, invalid, fieldSize = 'lg', trailing, ...props },
  ref,
) {
  return (
    <div className="relative flex items-center">
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          'w-full rounded-md border bg-surface px-4 text-body-md text-primary',
          'transition-colors duration-fast ease-standard',
          'disabled:cursor-not-allowed disabled:bg-subtle disabled:text-tertiary',
          fieldSize === 'lg' ? 'h-control-lg' : 'h-control-md',
          invalid ? 'border-danger' : 'border-border-strong',
          trailing && 'pr-touch',
          className,
        )}
        {...props}
      />
      {trailing ? <div className="absolute right-0 flex items-center">{trailing}</div> : null}
    </div>
  )
})

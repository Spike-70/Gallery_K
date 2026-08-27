import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'
import { Icon } from '@/shared/ui/Icon'

/**
 * FieldGroup — 폼의 최소 단위(디자인 시스템 문서 §8.1)
 * 라벨·필드·힌트·오류의 수직 조합. 라벨은 항상 필드 **위**에 둔다.
 * 플로팅 라벨을 쓰지 않는다 — 축소된 라벨이 12px 이하가 되어 DS-3과 충돌한다.
 */
export type FieldGroupProps = {
  ref?: React.Ref<HTMLDivElement>
  id: string
  label: string
  hint?: ReactNode
  error?: string
  /** 우하단 글자 수 카운터 등 */
  trailing?: ReactNode
  /** 레이아웃에는 영향이 없다. 필수 표시는 입력 요소의 `required`가 담당한다. */
  required?: boolean
  children: ReactNode
  className?: string
}

export function fieldIds(id: string) {
  return { hintId: `${id}-hint`, errorId: `${id}-error` }
}

export function FieldGroup({ id, label, hint, error, trailing, children, className, ref }: FieldGroupProps) {
  const { hintId, errorId } = fieldIds(id)
  return (
    <div ref={ref} className={cn('flex flex-col gap-2', className)}>
      {/*
        필수 여부는 라벨 텍스트가 아니라 입력 요소의 `required`가 전달한다.
        라벨에 "(필수)"를 덧붙이면 스크린리더가 모든 필드에서 그 말을 반복한다.
      */}
      <label htmlFor={id} className="text-label text-secondary">
        {label}
      </label>

      {children}

      {(hint || trailing || error) && (
        <div className="flex items-start justify-between gap-2">
          <div className="gk-slot-hint flex-1">
            {error ? (
              // 오류는 경계선 색 + 아이콘 + 메시지의 3중 표기다(DS-5).
              <p id={errorId} role="alert" className="flex items-center gap-1 text-caption text-danger">
                <Icon name="alert" size="sm" className="h-4 w-4" />
                {error}
              </p>
            ) : hint ? (
              <p id={hintId} className="text-caption text-tertiary">
                {hint}
              </p>
            ) : null}
          </div>
          {trailing}
        </div>
      )}
    </div>
  )
}

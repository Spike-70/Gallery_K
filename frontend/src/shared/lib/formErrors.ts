import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'

/**
 * 서버 오류 → 폼 표시 — 프런트엔드 아키텍처 문서 §7.2
 *
 * | 조건 | 표시 |
 * |---|---|
 * | `field_errors`가 있다 | 각 필드 옆 인라인(RHF `setError`) |
 * | 폼 맥락이고 `field_errors`가 없다 | 폼 상단 배너 |
 *
 * **이 두 갈래 외의 오류 표시 경로를 만들지 않는다**(API 문서 §2.5).
 */
export function applyApiError<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  /** 서버 필드명(snake_case) → 폼 필드명. 다르면 여기서만 잇는다. */
  fieldMap: Record<string, string> = {},
): string | null {
  if (!isApiError(error)) return resolveErrorMessage(error)

  if (error.hasFieldErrors) {
    for (const fieldError of error.fieldErrors) {
      const name = (fieldMap[fieldError.field] ?? toCamelCase(fieldError.field)) as Path<T>
      setError(name, { type: 'server', message: fieldError.message })
    }
    return null
  }

  return resolveErrorMessage(error)
}

function toCamelCase(field: string): string {
  return field.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())
}

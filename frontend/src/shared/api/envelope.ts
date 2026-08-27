/**
 * 표준 응답 봉투 — API 명세서 §2.2
 * 성공·실패의 키 집합이 완전히 동일하므로 `success` 하나로 판별한다.
 */

import type { IsoDate, IsoDateTime, Nullable } from '@/shared/types/utility'

/** §2.4 페이지네이션 */
export type PaginationMeta = {
  mode: 'cursor' | 'page'
  limit: number
  count: number
  has_more: boolean
  next_cursor: Nullable<string>
  page: Nullable<number>
  total_count: Nullable<number>
  total_pages: Nullable<number>
}

/** §2.3 meta */
export type ResponseMeta = {
  request_id: string
  server_time: IsoDateTime
  /** 서버 기준 KST 오늘. **클라이언트는 단말 시계로 날짜를 계산하지 않는다**(PRD §6.1) */
  server_date: IsoDate
  api_version: string
  pagination?: Nullable<PaginationMeta>
  deprecation?: Nullable<{ sunset_on: IsoDate; replacement: string }>
}

/** §2.5 field_errors[] */
export type FieldError = {
  field: string
  code: 'REQUIRED' | 'TOO_LONG' | 'TOO_SHORT' | 'INVALID_FORMAT' | 'OUT_OF_RANGE' | 'NOT_ALLOWED'
  message: string
  limit: Nullable<number>
}

/** §2.5 error */
export type ErrorBody = {
  code: string
  /** 최종 사용자에게 그대로 보여줄 수 있는 한국어 문장 */
  message: string
  field_errors: Nullable<FieldError[]>
  details: Nullable<Record<string, unknown>>
  retryable: boolean
  doc_hint: Nullable<string>
}

export type SuccessEnvelope<T> = {
  success: true
  data: T
  meta: ResponseMeta
  error: null
}

export type FailureEnvelope = {
  success: false
  data: null
  meta: ResponseMeta
  error: ErrorBody
}

export type ApiEnvelope<T> = SuccessEnvelope<T> | FailureEnvelope

export function isSuccessEnvelope<T>(envelope: ApiEnvelope<T>): envelope is SuccessEnvelope<T> {
  return envelope.success === true
}

/** 목·테스트에서 봉투를 만들 때 쓰는 헬퍼. 프로덕션 코드가 봉투를 조립하지 않는다. */
export function createMeta(overrides: Partial<ResponseMeta> = {}): ResponseMeta {
  const now = new Date()
  return {
    request_id: `mock-${now.getTime().toString(36)}`,
    server_time: now.toISOString(),
    server_date: now.toISOString().slice(0, 10),
    api_version: 'v1',
    pagination: null,
    deprecation: null,
    ...overrides,
  }
}

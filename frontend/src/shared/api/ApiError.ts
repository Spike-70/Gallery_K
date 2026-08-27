import type { ErrorBody, FieldError } from '@/shared/api/envelope'

/**
 * API 오류 객체 — 프런트엔드 아키텍처 문서 §7.1
 * 화면은 항상 `code`로 분기하고, 문구는 `message`를 그대로 쓴다(API 문서 AP-2).
 */

/** 프런트엔드가 생성하는 코드. 서버 카탈로그에는 등록되지 않는다(API 문서 §5.2 각주). */
export const CLIENT_ERROR_CODES = {
  networkOffline: 'NETWORK_OFFLINE',
  clientTimeout: 'CLIENT_TIMEOUT',
  chunkLoadFailed: 'CHUNK_LOAD_FAILED',
  unknown: 'CLIENT_UNKNOWN',
} as const

/** 서버 오류 코드 중 화면이 직접 분기하는 것들 (API 문서 §5) */
export const ERROR_CODES = {
  validationFailed: 'VALIDATION_FAILED',
  notFound: 'NOT_FOUND',
  conflictVersion: 'CONFLICT_VERSION',
  rateLimited: 'RATE_LIMITED',
  maintenance: 'MAINTENANCE_MODE',
  systemInternal: 'SYSTEM_INTERNAL',

  authRequired: 'AUTH_REQUIRED',
  authInvalidCredentials: 'AUTH_INVALID_CREDENTIALS',
  authTooManyAttempts: 'AUTH_TOO_MANY_ATTEMPTS',
  authSessionExpired: 'AUTH_SESSION_EXPIRED',
  authSessionRevoked: 'AUTH_SESSION_REVOKED',
  authForbidden: 'AUTH_FORBIDDEN',

  signupClosed: 'SIGNUP_CLOSED',
  signupPhoneTaken: 'SIGNUP_PHONE_TAKEN',
  passwordPolicyViolation: 'PASSWORD_POLICY_VIOLATION',
  passwordCurrentMismatch: 'PASSWORD_CURRENT_MISMATCH',
  resetCodeInvalid: 'RESET_CODE_INVALID',
  resetCodeExpired: 'RESET_CODE_EXPIRED',

  exhibitionNotFound: 'EXHIBITION_NOT_FOUND',
  exhibitionNotOpened: 'EXHIBITION_NOT_OPENED',
  exhibitionBackfillForbidden: 'EXHIBITION_BACKFILL_FORBIDDEN',
  artworkNotFound: 'ARTWORK_NOT_FOUND',
  draftTargetOccupied: 'DRAFT_TARGET_OCCUPIED',
  draftNotFound: 'DRAFT_NOT_FOUND',
  uploadFileTooLarge: 'UPLOAD_FILE_TOO_LARGE',
  uploadMimeNotAllowed: 'UPLOAD_MIME_NOT_ALLOWED',

  memberNotFound: 'MEMBER_NOT_FOUND',
  memberCuratorImmutable: 'MEMBER_CURATOR_IMMUTABLE',
  noticePeriodOverlap: 'NOTICE_PERIOD_OVERLAP',
  noticePeriodInvalid: 'NOTICE_PERIOD_INVALID',
  pushSubscriptionInvalid: 'PUSH_SUBSCRIPTION_INVALID',
} as const

export type ErrorCode = string

export class ApiError extends Error {
  readonly code: ErrorCode
  readonly status: number
  readonly fieldErrors: FieldError[]
  readonly details: Record<string, unknown> | null
  readonly retryable: boolean
  /** 사용자 문의를 서버 로그와 잇는 유일한 수단이다(API 문서 AP-7) */
  readonly requestId: string | null

  constructor(params: {
    code: ErrorCode
    message: string
    status: number
    fieldErrors?: FieldError[] | null
    details?: Record<string, unknown> | null
    retryable?: boolean
    requestId?: string | null
  }) {
    super(params.message)
    this.name = 'ApiError'
    this.code = params.code
    this.status = params.status
    this.fieldErrors = params.fieldErrors ?? []
    this.details = params.details ?? null
    this.retryable = params.retryable ?? false
    this.requestId = params.requestId ?? null
  }

  static fromEnvelope(error: ErrorBody, status: number, requestId: string | null): ApiError {
    return new ApiError({
      code: error.code,
      message: error.message,
      status,
      fieldErrors: error.field_errors,
      details: error.details,
      retryable: error.retryable,
      requestId,
    })
  }

  /** 세션이 끊긴 오류인지 — httpClient가 1회만 로그인으로 보낸다(§7.1) */
  get isSessionLost(): boolean {
    return (
      this.code === ERROR_CODES.authSessionExpired ||
      this.code === ERROR_CODES.authSessionRevoked ||
      this.code === ERROR_CODES.authRequired
    )
  }

  get hasFieldErrors(): boolean {
    return this.fieldErrors.length > 0
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

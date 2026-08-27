import { CLIENT_ERROR_CODES, ERROR_CODES, isApiError } from '@/shared/api/ApiError'

/**
 * 오류 코드 → 한국어 폴백 문구 — UX 문서 §5.4
 *
 * **서버 `error.message`를 우선 사용한다.** 이 맵은 네트워크 오류처럼 서버 문구가
 * 존재할 수 없는 경우와 목 데이터의 폴백일 뿐이다. 프런트가 코드별 문구를 자체
 * 정의해 서버와 어긋나는 상황을 만들지 않는다(프런트 §7.2).
 */
const FALLBACK_MESSAGES: Record<string, string> = {
  [ERROR_CODES.validationFailed]: '입력한 내용을 다시 확인해 주세요.',
  [ERROR_CODES.notFound]: '요청하신 내용을 찾을 수 없습니다.',
  [ERROR_CODES.conflictVersion]: '다른 곳에서 먼저 수정되었습니다. 새로고침 후 다시 시도해 주세요.',
  [ERROR_CODES.rateLimited]: '잠시 후 다시 시도해 주세요.',
  [ERROR_CODES.maintenance]: '잠시 점검 중입니다.',
  [ERROR_CODES.systemInternal]: '문제가 생겼습니다. 잠시 후 다시 시도해 주세요.',

  [ERROR_CODES.authRequired]: '로그인이 필요합니다.',
  [ERROR_CODES.authInvalidCredentials]: '전화번호 또는 비밀번호가 맞지 않습니다.',
  [ERROR_CODES.authTooManyAttempts]: '로그인 시도가 많았습니다. 10분 뒤에 다시 시도해 주세요.',
  [ERROR_CODES.authSessionExpired]: '로그인이 만료되었습니다. 다시 입장해 주세요.',
  [ERROR_CODES.authSessionRevoked]: '로그인이 만료되었습니다. 다시 입장해 주세요.',
  [ERROR_CODES.authForbidden]: '접근 권한이 없습니다.',

  [ERROR_CODES.signupClosed]: '지금은 새로운 회원을 받고 있지 않습니다.',
  [ERROR_CODES.signupPhoneTaken]: '이미 가입된 번호입니다.',
  [ERROR_CODES.passwordPolicyViolation]: '8자 이상 입력해 주세요.',
  [ERROR_CODES.passwordCurrentMismatch]: '현재 비밀번호가 맞지 않습니다.',
  [ERROR_CODES.resetCodeInvalid]: '인증번호가 맞지 않습니다.',
  [ERROR_CODES.resetCodeExpired]: '인증번호가 만료되었습니다. 다시 받아 주세요.',

  [ERROR_CODES.exhibitionNotFound]: '전시를 찾을 수 없습니다.',
  [ERROR_CODES.exhibitionNotOpened]: '첫 전시를 준비하고 있습니다',
  [ERROR_CODES.exhibitionBackfillForbidden]:
    '지난 날짜에는 새 전시를 걸 수 없습니다. 오늘 날짜로 이어서 쓰실 수 있습니다.',
  [ERROR_CODES.artworkNotFound]: '그림을 찾을 수 없습니다.',
  [ERROR_CODES.draftTargetOccupied]: '오늘 날짜에 이미 작업 중인 전시가 있습니다.',
  [ERROR_CODES.draftNotFound]: '이어 쓸 작업물이 없습니다.',
  [ERROR_CODES.uploadFileTooLarge]: '20MB까지 올릴 수 있습니다.',
  [ERROR_CODES.uploadMimeNotAllowed]: 'JPG, PNG, WebP 파일만 올릴 수 있습니다.',

  [ERROR_CODES.memberNotFound]: '회원을 찾을 수 없습니다.',
  [ERROR_CODES.memberCuratorImmutable]: '관리자 계정은 변경할 수 없습니다.',
  [ERROR_CODES.noticePeriodOverlap]: '이미 같은 기간에 공지가 있습니다.',
  [ERROR_CODES.noticePeriodInvalid]: '종료일은 시작일보다 빠를 수 없습니다.',
  [ERROR_CODES.pushSubscriptionInvalid]: '알림 설정에 실패했습니다. 다시 시도해 주세요.',

  [CLIENT_ERROR_CODES.networkOffline]: '연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.',
  [CLIENT_ERROR_CODES.clientTimeout]: '연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.',
  [CLIENT_ERROR_CODES.chunkLoadFailed]: '새 버전이 있습니다. 새로고침 후 다시 시도해 주세요.',
}

const GENERIC_MESSAGE = '문제가 생겼습니다. 잠시 후 다시 시도해 주세요.'

/** 표시할 문구 하나를 고른다. 서버 문구 > 폴백 맵 > 일반 문구 순. */
export function resolveErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.message) return error.message
    return FALLBACK_MESSAGES[error.code] ?? GENERIC_MESSAGE
  }
  return GENERIC_MESSAGE
}

/** 코드만 알고 있을 때의 폴백 조회 (목 데이터 조립용) */
export function fallbackMessageFor(code: string): string {
  return FALLBACK_MESSAGES[code] ?? GENERIC_MESSAGE
}

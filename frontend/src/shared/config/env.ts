/**
 * 환경 변수 — 프런트엔드 아키텍처 문서 §15.1
 *
 * 부팅 시 필수 변수를 검증하고 실패하면 **명시적으로 죽는다.**
 * 누락된 변수로 런타임 중간에 실패하는 것보다 낫다.
 */

type AppEnv = 'dev' | 'staging' | 'prod'

type Env = {
  /** API 기준 URL. 동일 오리진 배포이므로 상대 경로가 기본이다(API 문서 §2.11). */
  apiBaseUrl: string
  appEnv: AppEnv
  /** 웹푸시 구독용 VAPID 공개키. 없으면 알림 기능이 비활성화된다. */
  vapidPublicKey: string | null
  /**
   * 데모 모드 스위치.
   *
   * ─── 데모 제거 절차 ───────────────────────────────────────────────
   * `.env`에 `VITE_USE_MOCK=false`를 두면 목 데이터 경로가 전부 차단된다.
   * 완전 제거는 `src/mocks/README.md`의 3단계를 따른다.
   * ────────────────────────────────────────────────────────────────
   */
  useMock: boolean
}

function required(key: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`[env] 필수 환경 변수가 없습니다: ${key}`)
  }
  return value
}

function optional(value: string | undefined): string | null {
  return value && value.length > 0 ? value : null
}

function toBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback
  return value === 'true' || value === '1'
}

const rawAppEnv = (import.meta.env.VITE_APP_ENV ?? 'dev') as AppEnv

export const env: Env = {
  apiBaseUrl: required('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL ?? '/api'),
  appEnv: rawAppEnv,
  vapidPublicKey: optional(import.meta.env.VITE_VAPID_PUBLIC_KEY),
  // 데모 단계의 기본값은 true다. 백엔드 연동 시 false로 바꾼다.
  useMock: toBoolean(import.meta.env.VITE_USE_MOCK, true),
}

export const isProduction = env.appEnv === 'prod'

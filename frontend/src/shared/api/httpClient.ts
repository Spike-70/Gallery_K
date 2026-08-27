import { ApiError, CLIENT_ERROR_CODES } from '@/shared/api/ApiError'
import { type ApiEnvelope, type ResponseMeta, isSuccessEnvelope } from '@/shared/api/envelope'
import { fallbackMessageFor } from '@/shared/api/errorMessages'
import { env } from '@/shared/config/env'
import { logger } from '@/shared/lib/logger'

/**
 * HTTP 클라이언트 — 프런트엔드 아키텍처 문서 §7.1
 *
 * 책임
 *  1. 기본 URL · `credentials: 'include'` · `X-Requested-With` 헤더 부착
 *  2. 응답 봉투 해석 → 성공이면 `data`만, 실패면 `ApiError` throw
 *  3. `304` 처리(Query 캐시 유지)
 *  4. 네트워크 오류를 `NETWORK_OFFLINE`으로 정규화
 *  5. 세션 소실 시 **1회만** 세션 초기화·로그인 이동을 트리거
 *  6. `meta.request_id` 보존
 *  7. 요청 타임아웃 10초
 *
 * **이 모듈 바깥에서 `fetch`를 직접 호출하지 않는다.** 예외는 서비스워커와
 * S3 직접 업로드 두 곳뿐이며 각각 별도 모듈에 격리되어 있다.
 */

const TIMEOUT_MS = 10_000
const CSRF_HEADER = { 'X-Requested-With': 'gallery-k' } as const

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type RequestOptions = {
  method?: HttpMethod
  body?: unknown
  query?: Record<string, string | number | boolean | undefined | null>
  signal?: AbortSignal
  /** `304` 조건부 요청용 */
  etag?: string
}

/** 응답 봉투 전체가 필요할 때(페이지네이션 meta 등) 쓰는 반환 형태 */
export type HttpResult<T> = {
  data: T
  meta: ResponseMeta
}

/**
 * 세션 소실 처리기.
 * `shared`는 상위 레이어를 import 할 수 없으므로(FA-1) 앱이 부팅할 때 주입한다.
 */
type SessionLostHandler = () => void
let sessionLostHandler: SessionLostHandler | null = null
let sessionLostTriggered = false

export function registerSessionLostHandler(handler: SessionLostHandler): void {
  sessionLostHandler = handler
}

/** 로그인 성공 등 세션이 회복되면 다시 무장한다. */
export function resetSessionLostGuard(): void {
  sessionLostTriggered = false
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = `${env.apiBaseUrl}${path}`
  if (!query) return base
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    params.append(key, String(value))
  }
  const queryString = params.toString()
  return queryString ? `${base}?${queryString}` : base
}

function normalizeUnknownError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (error instanceof DOMException && error.name === 'AbortError') {
    return new ApiError({
      code: CLIENT_ERROR_CODES.clientTimeout,
      message: fallbackMessageFor(CLIENT_ERROR_CODES.clientTimeout),
      status: 0,
      retryable: true,
    })
  }

  return new ApiError({
    code: CLIENT_ERROR_CODES.networkOffline,
    message: fallbackMessageFor(CLIENT_ERROR_CODES.networkOffline),
    status: 0,
    retryable: true,
  })
}

/** `304 Not Modified` — 봉투 규약의 유일한 예외다(API 문서 §2.9). */
export class NotModifiedError extends Error {
  constructor() {
    super('NOT_MODIFIED')
    this.name = 'NotModifiedError'
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<HttpResult<T>> {
  const { method = 'GET', body, query, signal, etag } = options

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), TIMEOUT_MS)
  if (signal) {
    signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  try {
    const response = await fetch(buildUrl(path, query), {
      method,
      // 세션·미디어 쿠키는 HttpOnly다. JS는 토큰에 접근하지 않는다(§12).
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(method === 'GET' ? {} : CSRF_HEADER),
        ...(etag ? { 'If-None-Match': etag } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })

    if (response.status === 304) {
      throw new NotModifiedError()
    }

    const requestId = response.headers.get('X-Request-Id')
    const envelope = (await response.json()) as ApiEnvelope<T>

    if (!isSuccessEnvelope(envelope)) {
      const apiError = ApiError.fromEnvelope(
        envelope.error,
        response.status,
        envelope.meta?.request_id ?? requestId,
      )
      if (apiError.isSessionLost && !sessionLostTriggered) {
        sessionLostTriggered = true
        sessionLostHandler?.()
      }
      throw apiError
    }

    return { data: envelope.data, meta: envelope.meta }
  } catch (error) {
    if (error instanceof NotModifiedError) throw error
    const normalized = normalizeUnknownError(error)
    logger.warn('request failed', path, normalized.code)
    throw normalized
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export const httpClient = {
  /** 봉투의 `data`만 필요할 때 */
  async get<T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    const result = await request<T>(path, { ...options, method: 'GET' })
    return result.data
  },
  async post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    const result = await request<T>(path, { ...options, method: 'POST', body })
    return result.data
  },
  async put<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    const result = await request<T>(path, { ...options, method: 'PUT', body })
    return result.data
  },
  async patch<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    const result = await request<T>(path, { ...options, method: 'PATCH', body })
    return result.data
  },
  async delete<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    const result = await request<T>(path, { ...options, method: 'DELETE', body })
    return result.data
  },

  /** `meta.pagination`이 필요한 목록 조회 */
  requestWithMeta: request,

  /**
   * 기록 API 전용 — 화면 이탈 중에도 전송된다(프런트 §9.3).
   * 실패해도 조용히 포기한다. 사용자에게 오류를 보여주지 않는다.
   *
   * `navigator.sendBeacon`을 쓰지 않는다 — 커스텀 헤더를 실을 수 없어
   * 서버의 변경 요청 검사(`X-Requested-With`)에 걸린다(API 문서 §2.7).
   * `keepalive`가 같은 일(이탈 후 전송)을 하면서 헤더를 보낼 수 있다.
   */
  beacon(path: string): void {
    try {
      void fetch(buildUrl(path), {
        method: 'POST',
        credentials: 'include',
        headers: CSRF_HEADER,
        keepalive: true,
      }).catch(() => undefined)
    } catch (error) {
      logger.debug('beacon failed', path, error)
    }
  },
}

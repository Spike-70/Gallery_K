import { vi } from 'vitest'

import { createMeta } from '@/shared/api/envelope'
import type { ErrorBody, PaginationMeta } from '@/shared/api/envelope'

/**
 * 통합 테스트용 API 스텁 — 프런트엔드 아키텍처 문서 §14
 *
 * 화면은 `httpClient`를 거쳐 `fetch` 하나로만 서버에 닿는다(§7.1). 그래서 테스트가
 * 가로챌 지점도 하나뿐이다 — **화면·훅·매퍼는 실제 코드 그대로 돌고**, 경계에서만
 * 서버 원형(snake_case) 응답이 들어간다. 매퍼가 테스트에서도 함께 검증된다.
 *
 * 경로는 `endpoints.ts`가 만드는 그대로 쓰고, 경로 변수는 `{name}`으로 적는다.
 *
 * ```ts
 * const api = stubApi({
 *   'GET /exhibitions/current': () => currentExhibition(),
 *   'POST /exhibitions/{date}/view': () => ({ entered: true }),
 * })
 * expect(api.called('POST /exhibitions/{date}/view')).toBe(true)
 * ```
 */

export type RequestContext = {
  params: Record<string, string>
  query: URLSearchParams
  body: unknown
}

/** 응답 `data`를 돌려준다. 페이지네이션이 필요하면 `paged()`로 감싼다. */
export type RouteHandler = (context: RequestContext) => unknown

export type ApiRoutes = Record<string, RouteHandler>

export type RecordedCall = {
  key: string
  method: string
  path: string
  query: URLSearchParams
  body: unknown
}

export type ApiStub = {
  calls: RecordedCall[]
  called: (key: string) => boolean
  callsFor: (key: string) => RecordedCall[]
}

const PAGED = Symbol('paged')

type PagedResult = { [PAGED]: true; data: unknown; pagination: PaginationMeta }

/** 목록 응답에 `meta.pagination`을 붙인다(API 문서 §2.4). */
export function paged(data: unknown, pagination: Partial<PaginationMeta> = {}): PagedResult {
  return {
    [PAGED]: true,
    data,
    pagination: {
      mode: 'cursor',
      limit: 30,
      count: 0,
      has_more: false,
      next_cursor: null,
      page: null,
      total_count: null,
      total_pages: null,
      ...pagination,
    },
  }
}

/** 오류 봉투를 던진다. 화면의 오류 분기를 테스트에서 확인할 수 있다. */
export function apiError(code: string, message: string, status = 400): never {
  throw new StubApiError(code, message, status)
}

class StubApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'StubApiError'
    this.code = code
    this.status = status
  }
}

/** `/api/exhibitions/2026-08-28` → `/exhibitions/2026-08-28` */
function toApiPath(rawUrl: string): { path: string; query: URLSearchParams } {
  const url = new URL(rawUrl, 'http://localhost')
  return {
    path: url.pathname.replace(/^\/api/, '') || '/',
    query: url.searchParams,
  }
}

function matchRoute(
  pattern: string,
  method: string,
  path: string,
): Record<string, string> | null {
  const [patternMethod, patternPath] = pattern.split(' ')
  if (patternMethod !== method) return null

  const patternParts = patternPath.split('/')
  const pathParts = path.split('/')
  if (patternParts.length !== pathParts.length) return null

  const params: Record<string, string> = {}
  for (let index = 0; index < patternParts.length; index += 1) {
    const expected = patternParts[index]
    const actual = pathParts[index]
    if (expected.startsWith('{') && expected.endsWith('}')) {
      params[expected.slice(1, -1)] = decodeURIComponent(actual)
      continue
    }
    if (expected !== actual) return null
  }
  return params
}

function jsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-Id': 'test-request-id' },
  })
}

function failure(error: ErrorBody, status: number): Response {
  return jsonResponse({ success: false, data: null, meta: createMeta(), error }, status)
}

/**
 * `fetch`를 라우트 표로 대체한다. `vi.stubGlobal`을 쓰므로 `restoreAllMocks`가 되돌린다
 * (`vitest.config.ts`의 `unstubGlobals`).
 */
export function stubApi(routes: ApiRoutes): ApiStub {
  const calls: RecordedCall[] = []

  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const rawUrl = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const method = (init?.method ?? 'GET').toUpperCase()
    const { path, query } = toApiPath(rawUrl)
    const body = typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined

    for (const [key, handler] of Object.entries(routes)) {
      const params = matchRoute(key, method, path)
      if (params === null) continue

      calls.push({ key, method, path, query, body })
      try {
        const result = handler({ params, query, body })
        const isPaged = typeof result === 'object' && result !== null && PAGED in result
        const data = isPaged ? (result as PagedResult).data : result
        const pagination = isPaged ? (result as PagedResult).pagination : null
        return jsonResponse(
          { success: true, data, meta: createMeta({ pagination }), error: null },
          200,
        )
      } catch (error) {
        if (error instanceof StubApiError) {
          return failure(
            {
              code: error.code,
              message: error.message,
              field_errors: null,
              details: null,
              retryable: false,
              doc_hint: null,
            },
            error.status,
          )
        }
        throw error
      }
    }

    // 스텁하지 않은 경로를 부르면 조용히 통과시키지 않는다 — 화면이 무엇을 부르는지가 계약이다.
    return failure(
      {
        code: 'NOT_FOUND',
        message: `[apiStub] 스텁되지 않은 요청: ${method} ${path}`,
        field_errors: null,
        details: null,
        retryable: false,
        doc_hint: null,
      },
      404,
    )
  })

  return {
    calls,
    called: (key) => calls.some((call) => call.key === key),
    callsFor: (key) => calls.filter((call) => call.key === key),
  }
}

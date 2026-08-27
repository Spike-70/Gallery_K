import '@testing-library/jest-dom/vitest'

/**
 * 테스트 부트스트랩 — 프런트엔드 아키텍처 문서 §14
 * jsdom에 없는 브라우저 API를 최소한으로 채운다. 화면 코드가 이를 알 필요는 없다.
 */
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia
}

if (!window.localStorage) {
  // 이 jsdom 구성에는 웹 스토리지가 없다. 제품 코드는 안전 래퍼로 없어도 동작하지만
  // (`shared/lib/storage.ts`), 보존 자체를 검증하려면 실물이 필요하다.
  const createStorageStub = (): Storage => {
    const entries = new Map<string, string>()
    return {
      get length() {
        return entries.size
      },
      key: (index: number) => [...entries.keys()][index] ?? null,
      getItem: (key: string) => entries.get(key) ?? null,
      setItem: (key: string, value: string) => void entries.set(key, String(value)),
      removeItem: (key: string) => void entries.delete(key),
      clear: () => entries.clear(),
    } as Storage
  }

  Object.defineProperty(window, 'localStorage', { value: createStorageStub(), configurable: true })
  Object.defineProperty(window, 'sessionStorage', { value: createStorageStub(), configurable: true })
}

if (!window.requestIdleCallback) {
  window.requestIdleCallback = ((callback: () => void) => window.setTimeout(callback, 0)) as never
  window.cancelIdleCallback = ((id: number) => window.clearTimeout(id)) as never
}

if (!window.IntersectionObserver) {
  // jsdom에는 없다. 무한 스크롤 트리거는 통합 테스트의 관심사가 아니다.
  window.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
    readonly root = null
    readonly rootMargin = ''
    readonly thresholds: readonly number[] = []
  } as unknown as typeof window.IntersectionObserver
}

if (!globalThis.crypto?.subtle) {
  Object.defineProperty(globalThis, 'crypto', {
    value: { ...globalThis.crypto, subtle: { digest: async () => new ArrayBuffer(32) } },
  })
}

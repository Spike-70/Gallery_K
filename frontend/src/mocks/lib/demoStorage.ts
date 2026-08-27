/**
 * 데모 상태 보존 — ⚠ 데모 전용. 백엔드 연동 시 `src/mocks`와 함께 통째로 사라진다.
 *
 * 목 데이터는 메모리에만 있어서 새로고침하면 모두 초기화된다. 그러면 데모가
 * **PRD가 약속한 것과 정반대로 동작한다** — 90일 자동 로그인(GAP-14)을 보여주려는
 * 화면에서 새로고침 한 번에 로그인 화면으로 튕긴다. 열람 표식(PRD §6.5)도 마찬가지다.
 *
 * 그래서 세션과 열람 기록만 브라우저에 남긴다. 실제 서버가 소유할 상태(전시 원고,
 * 업로드한 이미지)는 **일부러 남기지 않는다** — 그것까지 흉내 내면 목이 백엔드가 되고,
 * 실제 API로 바꿀 때 지워야 할 코드가 늘어난다.
 *
 * 키는 전부 `gk.demo.` 로 시작한다. `localStorage.clear()` 없이도 골라 지울 수 있다.
 */

const PREFIX = 'gk.demo.'

export const DEMO_KEYS = {
  session: `${PREFIX}session`,
  viewedArtworks: `${PREFIX}viewed-artworks`,
  enteredDates: `${PREFIX}entered-dates`,
} as const

function safeLocalStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    // 사파리 프라이빗 모드 등. 데모는 메모리만으로도 동작해야 한다.
    return null
  }
}

export function readDemo<T>(key: string, fallback: T): T {
  const raw = safeLocalStorage()?.getItem(key)
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function writeDemo(key: string, value: unknown): void {
  try {
    safeLocalStorage()?.setItem(key, JSON.stringify(value))
  } catch {
    // 용량 초과 등. 데모가 멈출 이유는 아니다.
  }
}

export function clearDemo(): void {
  const storage = safeLocalStorage()
  if (!storage) return
  for (const key of Object.values(DEMO_KEYS)) storage.removeItem(key)
}

/**
 * 변경될 때마다 저장되는 `Set`.
 * 핸들러가 평소처럼 `add`/`delete` 만 부르면 보존은 저절로 이뤄진다.
 */
export class PersistentSet<T> extends Set<T> {
  // 생성자 매개변수 프로퍼티는 `erasableSyntaxOnly`가 막는다(타입만 지우면 되는 문법이 아니다).
  readonly storageKey: string

  constructor(storageKey: string) {
    // `new Set(iterable)`은 **재정의된 `add`를** 호출한다(ES 규격). 초기값을 super에 넘기면
    // `storageKey`가 대입되기 전에 `flush()`가 돌아 `undefined` 키에 쓴다.
    // 그래서 빈 Set으로 시작해 키를 먼저 세우고, 보존을 건너뛰는 `super.add`로 채운다.
    super()
    this.storageKey = storageKey
    for (const value of readDemo<T[]>(storageKey, [])) super.add(value)
  }

  private flush(): void {
    writeDemo(this.storageKey, [...this])
  }

  override add(value: T): this {
    super.add(value)
    this.flush()
    return this
  }

  override delete(value: T): boolean {
    const removed = super.delete(value)
    if (removed) this.flush()
    return removed
  }

  override clear(): void {
    super.clear()
    this.flush()
  }
}

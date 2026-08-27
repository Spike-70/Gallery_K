import { beforeEach, describe, expect, it } from 'vitest'

import { DEMO_KEYS, PersistentSet, clearDemo, readDemo, writeDemo } from '@/mocks/lib/demoStorage'

/**
 * 데모 보존 계층 — 데모의 신뢰성이 여기 하나에 달려 있다.
 * 새로고침에 로그인이 풀리면 90일 자동 로그인(PRD GAP-14)을 보여주려는 화면이
 * 정반대로 동작한다.
 */
describe('데모 상태 보존', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('세션을 저장하고 다음 부팅에서 그대로 읽는다', () => {
    writeDemo(DEMO_KEYS.session, { currentUserId: 'mb1' })
    expect(readDemo(DEMO_KEYS.session, null)).toEqual({ currentUserId: 'mb1' })
  })

  it('값이 깨져 있으면 기본값으로 물러선다 — 데모가 멈추지 않는다', () => {
    window.localStorage.setItem(DEMO_KEYS.session, '{ not json')
    expect(readDemo(DEMO_KEYS.session, 'fallback')).toBe('fallback')
  })

  it('열람 표식은 추가할 때마다 저장되고 다음 인스턴스에서 복원된다', () => {
    const first = new PersistentSet<string>(DEMO_KEYS.viewedArtworks)
    first.add('2026-08-27:art-1')
    first.add('2026-08-27:art-2')

    const restored = new PersistentSet<string>(DEMO_KEYS.viewedArtworks)
    expect([...restored]).toEqual(['2026-08-27:art-1', '2026-08-27:art-2'])
  })

  it('복원할 때 저장 키가 없는 상태로 쓰지 않는다', () => {
    // `new Set(iterable)`은 재정의된 `add`를 호출한다. 초기값을 super로 넘기면
    // 키가 대입되기 전에 저장이 일어나 `undefined` 키가 생긴다.
    writeDemo(DEMO_KEYS.enteredDates, ['2026-08-27'])
    const restored = new PersistentSet<string>(DEMO_KEYS.enteredDates)

    expect([...restored]).toEqual(['2026-08-27'])
    expect(window.localStorage.getItem('undefined')).toBeNull()
  })

  it('삭제도 반영한다', () => {
    const set = new PersistentSet<string>(DEMO_KEYS.enteredDates)
    set.add('2026-08-26')
    set.add('2026-08-27')
    set.delete('2026-08-26')

    expect([...new PersistentSet<string>(DEMO_KEYS.enteredDates)]).toEqual(['2026-08-27'])
  })

  it('데모 키만 지운다 — 제품 코드의 키는 건드리지 않는다', () => {
    window.localStorage.setItem('gk.font-scale', 'large')
    writeDemo(DEMO_KEYS.session, { currentUserId: 'mb1' })

    clearDemo()

    expect(window.localStorage.getItem(DEMO_KEYS.session)).toBeNull()
    expect(window.localStorage.getItem('gk.font-scale')).toBe('large')
  })
})

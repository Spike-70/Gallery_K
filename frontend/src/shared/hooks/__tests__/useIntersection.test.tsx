import { render, screen } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useIntersection } from '@/shared/hooks/useIntersection'

/**
 * 무한 스크롤 감시자 — 프런트엔드 아키텍처 문서 §9.2
 *
 * 이 훅이 조용히 실패하면 **목록이 더 이상 자라지 않는다.** 오류도, 로그도 없다.
 * 실제로 그렇게 죽어 있었던 자리가 관리자 달력의 과거 방향이었다(PRD GAP-7).
 */
const observed: Element[] = []

beforeEach(() => {
  observed.length = 0
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(_callback: IntersectionObserverCallback) {}
      observe(element: Element) {
        observed.push(element)
      }
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return []
      }
      readonly root = null
      readonly rootMargin = ''
      readonly thresholds: readonly number[] = []
    },
  )
})

function Late({ show }: { show: boolean }) {
  const { ref } = useIntersection()
  return <div>{show ? <div ref={ref} data-testid="sentinel" /> : null}</div>
}

describe('useIntersection', () => {
  it('첫 렌더에 없던 감시 대상이 나중에 붙어도 관찰한다', () => {
    const { rerender } = render(<Late show={false} />)
    expect(observed).toHaveLength(0)

    // 데이터가 도착한 뒤에야 센티넬이 렌더되는 것이 목록 화면의 정상 흐름이다.
    rerender(<Late show />)

    expect(screen.getByTestId('sentinel')).toBeInTheDocument()
    expect(observed).toHaveLength(1)
  })

  it('감시 대상이 사라지면 관찰을 멈춘다', () => {
    function Toggle() {
      const [show, setShow] = useState(true)
      const { ref } = useIntersection()
      return (
        <>
          <button type="button" onClick={() => setShow(false)}>
            hide
          </button>
          {show ? <div ref={ref} /> : null}
        </>
      )
    }

    render(<Toggle />)
    expect(observed).toHaveLength(1)
    screen.getByRole('button', { name: 'hide' }).click()
    // 감시자는 끊어지고 새 관찰은 생기지 않는다.
    expect(observed).toHaveLength(1)
  })
})

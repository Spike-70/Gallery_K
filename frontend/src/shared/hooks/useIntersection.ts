import { useCallback, useRef, useState } from 'react'

/**
 * 뷰포트 진입 감지 — 지연 로딩·무한 스크롤 트리거(프런트 §9.2).
 *
 * **콜백 ref를 돌려준다.** `RefObject`를 받는 형태는 감시 대상이 조건부로 렌더될 때
 * 조용히 실패한다 — 첫 렌더에 `ref.current`가 없으면 `useEffect`가 그냥 빠져나가고,
 * ref 객체의 정체성은 바뀌지 않으므로 **요소가 나중에 붙어도 다시 실행되지 않는다.**
 * 감시자가 안 붙었다는 신호는 어디에도 없고, 무한 스크롤이 조용히 죽는다.
 *
 * 콜백 ref는 요소가 붙고 떨어지는 그 순간에 호출되므로 이 함정이 없다.
 */
export function useIntersection(options: IntersectionObserverInit = { rootMargin: '200px' }): {
  ref: (node: Element | null) => void
  intersecting: boolean
} {
  const [intersecting, setIntersecting] = useState(false)
  const observerRef = useRef<IntersectionObserver | null>(null)
  // 옵션은 호출부에서 안정적으로 넘긴다. 매 렌더 새 객체를 만들면 감시자가 계속 재생성된다.
  const optionsRef = useRef(options)

  const ref = useCallback((node: Element | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null

    if (!node) {
      setIntersecting(false)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => setIntersecting(entry.isIntersecting),
      optionsRef.current,
    )
    observer.observe(node)
    observerRef.current = observer
  }, [])

  return { ref, intersecting }
}

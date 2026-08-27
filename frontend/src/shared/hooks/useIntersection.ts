import { type RefObject, useEffect, useState } from 'react'

/** 뷰포트 진입 감지 — 지연 로딩·무한 스크롤 트리거(프런트 §9.2). */
export function useIntersection(
  ref: RefObject<Element | null>,
  options: IntersectionObserverInit = { rootMargin: '200px' },
): boolean {
  const [intersecting, setIntersecting] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new IntersectionObserver(([entry]) => setIntersecting(entry.isIntersecting), options)
    observer.observe(element)
    return () => observer.disconnect()
    // options 객체는 호출부에서 안정적으로 넘긴다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref])

  return intersecting
}

import { useEffect, useState } from 'react'

/** 미디어 쿼리 구독. 레이아웃 분기(관리자 PC 좌우 분할 등)에 쓴다. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === 'undefined' ? false : window.matchMedia(query).matches,
  )

  useEffect(() => {
    const list = window.matchMedia(query)
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches)
    list.addEventListener('change', onChange)
    return () => list.removeEventListener('change', onChange)
  }, [query])

  return matches
}

/** 디자인 시스템 §5.2 브레이크포인트 */
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)')

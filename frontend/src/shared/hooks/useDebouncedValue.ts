import { useEffect, useState } from 'react'

/** 값이 멈춘 뒤에만 통과시킨다. 자동 저장 디바운스의 기반(UX §3.12). */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}

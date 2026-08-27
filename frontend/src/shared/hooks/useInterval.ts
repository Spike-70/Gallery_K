import { useEffect, useRef } from 'react'

/** 지연을 `null`로 주면 멈춘다. 폴링 종료 조건을 호출부가 소유한다. */
export function useInterval(callback: () => void, delayMs: number | null): void {
  const saved = useRef(callback)

  useEffect(() => {
    saved.current = callback
  }, [callback])

  useEffect(() => {
    if (delayMs === null) return
    const id = window.setInterval(() => saved.current(), delayMs)
    return () => window.clearInterval(id)
  }, [delayMs])
}

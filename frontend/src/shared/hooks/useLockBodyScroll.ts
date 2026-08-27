import { useEffect } from 'react'

/** 오버레이가 열려 있는 동안 body 스크롤을 잠근다(디자인 시스템 §8.1). */
export function useLockBodyScroll(locked: boolean): void {
  useEffect(() => {
    if (!locked) return
    const original = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = original
    }
  }, [locked])
}

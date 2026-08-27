import { useEffect } from 'react'

/** 앱이 포그라운드로 복귀했을 때(미디어 쿠키 갱신·전시 재확인) */
export function useVisibilityChange(onVisible: () => void): void {
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState === 'visible') onVisible()
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [onVisible])
}

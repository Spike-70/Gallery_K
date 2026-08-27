import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

import { SESSION_KEYS, sessionStore } from '@/shared/lib/storage'

/**
 * 스크롤 복원 — 프런트엔드 아키텍처 문서 §8.3
 *
 * C(그리드) → C-2(그림) → 뒤로가기에서 **보고 있던 자리로 돌아온다.** 이것이 없으면
 * 12점을 훑는 동안 매번 맨 위에서 다시 내려와야 하고, 그것만으로 완주율이 무너진다.
 *
 * 이미지 지연 로딩 때문에 높이는 나중에 확정된다. 그리드가 **종횡비로 높이를 미리
 * 예약**하므로(§9.2) 복원이 어긋나지 않는다.
 *
 * 새 화면으로 들어갈 때(`PUSH`)는 맨 위에서 시작하고, 뒤로가기(`POP`)일 때만 복원한다.
 */
export function useScrollRestoration(key: string): void {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    const storageKey = `${SESSION_KEYS.scrollOffset}:${key}`

    if (navigationType === 'POP') {
      const saved = Number(sessionStore.get(storageKey) ?? '0')
      if (saved > 0) {
        // 레이아웃이 확정된 뒤에 옮긴다. 같은 프레임에 옮기면 높이가 0이라 무시된다.
        requestAnimationFrame(() => window.scrollTo({ top: saved }))
      }
    }

    const remember = () => sessionStore.set(storageKey, String(window.scrollY))
    window.addEventListener('scroll', remember, { passive: true })
    return () => {
      remember()
      window.removeEventListener('scroll', remember)
    }
  }, [key, pathname, navigationType])
}

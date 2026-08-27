import { type ReactNode, useEffect } from 'react'

import { useSessionStore } from '@/entities/session/model/sessionStore'
import { STORAGE_KEYS, localStore } from '@/shared/lib/storage'
import type { FontScale } from '@/shared/types/enums'

/**
 * 큰 글씨 모드 — 프런트엔드 아키텍처 문서 §11
 *
 * `html[data-font-scale]` 하나만 동기화한다. 타이포 스케일도 그리드 열 수도
 * 이 속성 하나로 바뀐다(디자인 시스템 §11.3).
 *
 * **서버 값(`user.fontScale`)이 원천**이고 로컬 캐시는 초기 깜빡임 방지용이다.
 */
export function FontScaleProvider({ children }: { children: ReactNode }) {
  const fontScale = useSessionStore((state) => state.user?.fontScale)

  useEffect(() => {
    const cached = localStore.get(STORAGE_KEYS.fontScale) as FontScale | null
    const effective: FontScale = fontScale ?? cached ?? 'normal'
    document.documentElement.dataset.fontScale = effective
  }, [fontScale])

  return <>{children}</>
}

/** 세션 확인 전에도 캐시된 값으로 먼저 그린다(부팅 깜빡임 방지). */
export function applyCachedFontScale(): void {
  const cached = localStore.get(STORAGE_KEYS.fontScale)
  document.documentElement.dataset.fontScale = cached === 'large' ? 'large' : 'normal'
}

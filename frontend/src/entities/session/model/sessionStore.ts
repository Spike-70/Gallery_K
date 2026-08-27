import { create } from 'zustand'

import type { SessionUser } from '@/entities/session/model/types'
import { STORAGE_KEYS, localStore } from '@/shared/lib/storage'

/**
 * 세션 스토어 — 프런트엔드 아키텍처 문서 §6.2
 *
 * 서버 상태이기도 하지만 **라우팅 가드가 동기적으로 읽어야 하므로** 스토어에
 * 미러링한다. 원천은 Query이고 스토어는 그 구독 결과를 반영할 뿐이다.
 */
export type SessionStatus = 'booting' | 'authenticated' | 'anonymous'

type SessionState = {
  status: SessionStatus
  user: SessionUser | null
  mediaExpiresAt: string | null
  setAuthenticated: (user: SessionUser, mediaExpiresAt: string | null) => void
  setAnonymous: () => void
  updateUser: (user: SessionUser) => void
}

export const useSessionStore = create<SessionState>((set) => ({
  status: 'booting',
  user: null,
  mediaExpiresAt: null,

  setAuthenticated: (user, mediaExpiresAt) => {
    // 다음 부팅에서 세션 확인과 전시 조회를 병렬로 시작하기 위한 마커다(§8.2).
    localStore.set(STORAGE_KEYS.authHint, '1')
    localStore.set(STORAGE_KEYS.fontScale, user.fontScale)
    set({ status: 'authenticated', user, mediaExpiresAt })
  },

  setAnonymous: () => {
    localStore.remove(STORAGE_KEYS.authHint)
    set({ status: 'anonymous', user: null, mediaExpiresAt: null })
  },

  updateUser: (user) => {
    localStore.set(STORAGE_KEYS.fontScale, user.fontScale)
    set((state) => (state.user ? { ...state, user } : state))
  },
}))

/** 이전 방문에서 인증된 적이 있는가 — 낙관적 병렬 부팅의 판단 근거 */
export function hasAuthHint(): boolean {
  return localStore.get(STORAGE_KEYS.authHint) === '1'
}

/** 컴포넌트 밖(가드·httpClient 핸들러)에서 읽는 진입점 */
export const sessionSnapshot = () => useSessionStore.getState()

import { create } from 'zustand'

import { TOAST_DURATION } from '@/shared/config/constants'

/**
 * 토스트 스토어 — 프런트엔드 아키텍처 문서 §6.2
 *
 * **동시 1개**이며 새 토스트가 이전을 대체한다(디자인 시스템 §8.1).
 * 관람자 화면에는 성공 토스트가 없다 — 그림을 보는 일에 시스템이 끼어들지 않는다(UX §6).
 */
export type ToastTone = 'info' | 'error'

export type Toast = {
  id: number
  message: string
  tone: ToastTone
}

type ToastState = {
  toast: Toast | null
  show: (message: string, tone?: ToastTone) => void
  dismiss: () => void
}

let sequence = 0

export const useToastStore = create<ToastState>((set) => ({
  toast: null,
  show: (message, tone = 'info') => {
    sequence += 1
    set({ toast: { id: sequence, message, tone } })
  },
  dismiss: () => set({ toast: null }),
}))

/** 컴포넌트 밖(뮤테이션 핸들러 등)에서도 쓸 수 있는 진입점 */
export const toast = {
  info: (message: string) => useToastStore.getState().show(message, 'info'),
  error: (message: string) => useToastStore.getState().show(message, 'error'),
  duration: TOAST_DURATION,
}

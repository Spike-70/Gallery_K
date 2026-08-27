import { create } from 'zustand'

import type { Uuid } from '@/shared/types/utility'

/**
 * 전체화면 뷰어 스토어 — 프런트엔드 아키텍처 문서 §6.2
 * 라우팅과 무관한 오버레이이므로 URL 상태가 아니라 클라이언트 상태다.
 */
type ViewerState = {
  open: boolean
  artworkId: Uuid | null
  open_: (artworkId: Uuid) => void
  close: () => void
}

export const useViewerStore = create<ViewerState>((set) => ({
  open: false,
  artworkId: null,
  open_: (artworkId) => set({ open: true, artworkId }),
  close: () => set({ open: false, artworkId: null }),
}))

import type { ReactNode } from 'react'

import { ToastViewport } from '@/shared/ui'

/** 토스트 뷰포트를 앱 루트에 한 번만 마운트한다(동시 1개, 디자인 시스템 §8.1). */
export function ToastProvider({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <ToastViewport />
    </>
  )
}

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/app/App'
import { applyCachedFontScale } from '@/app/providers/FontScaleProvider'
import '@/styles/index.css'

/**
 * 부트스트랩 — 프런트엔드 아키텍처 문서 §8.2
 *
 * 세션 확인 전에 캐시된 큰 글씨 설정을 먼저 반영해 **초기 깜빡임을 막는다**(F-3).
 * 서버 값이 도착하면 `FontScaleProvider`가 덮어쓴다.
 */
applyCachedFontScale()

const container = document.getElementById('root')
if (!container) {
  throw new Error('[bootstrap] #root 를 찾을 수 없습니다.')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { type ComponentType, lazy } from 'react'

import { logger } from '@/shared/lib/logger'
import { SESSION_KEYS, sessionStore } from '@/shared/lib/storage'

/**
 * 청크 로드 실패 대응 — 프런트엔드 아키텍처 문서 §13
 *
 * 배포 직후에 흔하다. 브라우저가 들고 있는 `index.html`은 옛 해시를 가리키는데
 * 그 파일은 이미 사라져 있다. 사용자에게는 **아무 이유 없이 화면이 안 열리는 것**으로 보인다.
 *
 * **자동 새로고침은 한 번만** 한다. 실패가 배포 때문이 아니라면(오프라인 등) 새로고침이
 * 고쳐 주지 않으므로, 무한 새로고침 대신 라우트 오류 화면으로 넘긴다.
 */
const RELOAD_MARKER = `${SESSION_KEYS.chunkReload}`

export function lazyRoute<T extends ComponentType<unknown>>(load: () => Promise<{ default: T }>) {
  return lazy(async () => {
    try {
      const module = await load()
      // 성공했으면 다음 실패를 위해 기회를 되돌려 준다.
      sessionStore.remove(RELOAD_MARKER)
      return module
    } catch (error) {
      if (sessionStore.get(RELOAD_MARKER) === '1') {
        logger.warn('chunk load failed after reload', error)
        throw error
      }
      sessionStore.set(RELOAD_MARKER, '1')
      window.location.reload()
      // 새로고침이 진행되는 동안 렌더를 멈춘다.
      return new Promise<{ default: T }>(() => {})
    }
  })
}

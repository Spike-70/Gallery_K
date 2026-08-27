import { logger } from '@/shared/lib/logger'

/**
 * localStorage / sessionStorage 안전 래퍼 — 프런트엔드 아키텍처 문서 §3
 *
 * 사파리 프라이빗 모드·저장 용량 초과에서 접근 자체가 throw 한다.
 * **자격 정보는 저장하지 않는다**(§12). 토큰은 HttpOnly 쿠키에만 있다.
 */

/** 용도 키를 상수로 고정한다. 문자열을 사용처에서 조립하지 않는다. */
export const STORAGE_KEYS = {
  /** 이전 방문에서 인증됨 — 세션·전시 병렬 부팅 판단에 쓴다(§8.2) */
  authHint: 'gk.auth-hint',
  /** 큰 글씨 모드 초기 깜빡임 방지용 로컬 캐시. 원천은 서버 값이다(§11) */
  fontScale: 'gk.font-scale',
  /** 알림 권한 안내를 이미 보여줬는지 */
  notifyPromptSeen: 'gk.notify-prompt-seen',
  /** 전체화면 뷰어 확대 힌트 1회 노출 */
  zoomHintSeen: 'gk.zoom-hint-seen',
  /** 관리자 자동 저장 실패 시 로컬 보존 원고 (UX §3.12) */
  editorDraft: 'gk.editor-draft',
} as const

export const SESSION_KEYS = {
  /** 입장 기록 중복 억제 마커 — 세션당 날짜별 1회(§9.3) */
  enterLogged: 'gk.enter-logged',
  /** 그리드 스크롤 복원 (§8.3) */
  scrollOffset: 'gk.scroll',
  /** 청크 로드 실패로 자동 새로고침을 이미 한 번 했는가 (§13) */
  chunkReload: 'gk.chunk-reload',
} as const

function safeStorage(kind: 'local' | 'session'): Storage | null {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch (error) {
    logger.warn('storage unavailable', error)
    return null
  }
}

function createStorage(kind: 'local' | 'session') {
  return {
    get(key: string): string | null {
      try {
        return safeStorage(kind)?.getItem(key) ?? null
      } catch {
        return null
      }
    },
    set(key: string, value: string): void {
      try {
        safeStorage(kind)?.setItem(key, value)
      } catch (error) {
        logger.warn('storage write failed', key, error)
      }
    },
    remove(key: string): void {
      try {
        safeStorage(kind)?.removeItem(key)
      } catch {
        /* 저장소가 없어도 화면은 정상 동작해야 한다 */
      }
    },
    getJson<T>(key: string, fallback: T): T {
      const raw = this.get(key)
      if (raw === null) return fallback
      try {
        return JSON.parse(raw) as T
      } catch {
        return fallback
      }
    },
    setJson(key: string, value: unknown): void {
      try {
        this.set(key, JSON.stringify(value))
      } catch (error) {
        logger.warn('storage serialize failed', key, error)
      }
    },
  }
}

export const localStore = createStorage('local')
export const sessionStore = createStorage('session')

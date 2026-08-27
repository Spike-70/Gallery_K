/**
 * 플랫폼 감지 — PWA 설치 안내 분기 (프런트엔드 아키텍처 문서 §10.3)
 * iOS이고 standalone이 아니면 권한 요청 대신 홈 화면 추가를 먼저 안내한다.
 */

export function isIos(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  const isIpadOs = ua.includes('Macintosh') && 'ontouchend' in document
  return /iPad|iPhone|iPod/.test(ua) || isIpadOs
}

export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  const iosStandalone = (window.navigator as Navigator & { standalone?: boolean }).standalone
  return window.matchMedia('(display-mode: standalone)').matches || iosStandalone === true
}

/** 홈 화면 추가 안내를 먼저 보여야 하는 상황인지 */
export function needsIosInstallGuide(): boolean {
  return isIos() && !isStandalone()
}

export function supportsPush(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator
}

export function detectPushPlatform(): 'ios' | 'android' | 'desktop' | 'unknown' {
  if (typeof navigator === 'undefined') return 'unknown'
  if (isIos()) return 'ios'
  if (/Android/.test(navigator.userAgent)) return 'android'
  if (/Windows|Macintosh|Linux/.test(navigator.userAgent)) return 'desktop'
  return 'unknown'
}

/** 데이터 절약 모드에서는 프리페치를 전부 끈다 (프런트 §9.4) */
export function shouldPrefetch(): boolean {
  const connection = (
    navigator as Navigator & {
      connection?: { saveData?: boolean; effectiveType?: string }
    }
  ).connection
  if (!connection) return true
  if (connection.saveData) return false
  return connection.effectiveType !== '2g' && connection.effectiveType !== 'slow-2g'
}

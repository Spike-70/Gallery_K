import { logExhibitionView } from '@/entities/exhibition/api/exhibitionApi'
import { SESSION_KEYS, sessionStore } from '@/shared/lib/storage'
import type { IsoDate, Uuid } from '@/shared/types/utility'
import { logArtworkView } from '@/entities/artwork/api/artworkApi'

/**
 * 기록 전송 규칙 — 프런트엔드 아키텍처 문서 §9.3
 *
 * | 기록 | 시점 | 조건 |
 * |---|---|---|
 * | 입장 | C 화면 첫 렌더 후 | 세션당 날짜별 1회 (`sessionStorage` 마커) |
 * | 열람 | C-2 진입 후 1.5초 체류 | 스와이프로 스쳐 지나간 그림은 세지 않는다 |
 *
 * 두 요청 모두 **실패해도 조용히 포기**한다. 사용자에게 오류를 보여주지 않는다(FA-7).
 *
 * 이 모듈은 **컨테이너 계층에서만** 호출된다. 순수 컴포넌트를 렌더하는 미리보기는
 * 자연히 기록 경로를 타지 않는다 — 별도 플래그로 억제하지 않는 것이 이 분리의 이점이다(§8.4).
 */

function enterMarkerKey(date: IsoDate): string {
  return `${SESSION_KEYS.enterLogged}:${date}`
}

/** 이미 이번 세션에서 기록한 날짜인가 */
export function hasLoggedEntry(date: IsoDate): boolean {
  return sessionStore.get(enterMarkerKey(date)) === '1'
}

export function trackExhibitionEntry(date: IsoDate): void {
  if (hasLoggedEntry(date)) return
  sessionStore.set(enterMarkerKey(date), '1')
  void logExhibitionView(date)
}

export function trackArtworkView(artworkId: Uuid): void {
  void logArtworkView(artworkId)
}

import type { IsoDate, Uuid } from '@/shared/types/utility'

/**
 * 경로 상수 — 프런트엔드 아키텍처 문서 §5.1
 *
 * **경로 문자열은 이 파일에만 존재한다.** 모든 링크가 이 상수를 참조한다.
 *
 * 위치가 `shared`인 이유 — 경로는 도메인을 모르는 순수 상수이고, 화면(`features`)이
 * 링크를 만들려면 반드시 참조해야 한다. `app`에 두면 `features → app`이라는 역방향
 * 의존이 생겨 레이어 규칙(FA-1)이 깨진다. 라우트 **정의**는 `app/router`가 소유하고,
 * 라우트 **주소**는 여기가 소유한다.
 */
export const paths = {
  landing: '/',
  login: '/login',
  signup: '/signup',
  passwordReset: '/password/reset',
  passwordChange: '/password/change',

  gallery: '/gallery',
  galleryTheme: '/gallery/theme',
  galleryArtwork: (artworkId: Uuid) => `/gallery/artworks/${artworkId}`,

  archive: '/archive',
  archiveDate: (date: IsoDate) => `/archive/${date}`,
  archiveTheme: (date: IsoDate) => `/archive/${date}/theme`,
  archiveArtwork: (date: IsoDate, artworkId: Uuid) => `/archive/${date}/artworks/${artworkId}`,

  settings: '/settings',

  admin: '/admin',
  adminExhibition: (date: IsoDate) => `/admin/exhibitions/${date}`,
  adminExhibitionTheme: (date: IsoDate) => `/admin/exhibitions/${date}/theme`,
  adminExhibitionSlot: (date: IsoDate, position: number) => `/admin/exhibitions/${date}/slots/${position}`,
  adminExhibitionPreview: (date: IsoDate) => `/admin/exhibitions/${date}/preview`,
  adminMembers: '/admin/members',
  adminSettings: '/admin/settings',
  adminStats: '/admin/stats',
  adminMemberStats: (memberId: Uuid) => `/admin/stats/members/${memberId}`,
} as const

/** 라우트 패턴(정의용). 위 상수는 이동용이다. */
export const routePatterns = {
  galleryArtwork: '/gallery/artworks/:artworkId',
  archiveDate: '/archive/:date',
  archiveTheme: '/archive/:date/theme',
  archiveArtwork: '/archive/:date/artworks/:artworkId',
  adminExhibition: '/admin/exhibitions/:date',
  adminExhibitionTheme: '/admin/exhibitions/:date/theme',
  adminExhibitionSlot: '/admin/exhibitions/:date/slots/:position',
  adminExhibitionPreview: '/admin/exhibitions/:date/preview',
  adminMemberStats: '/admin/stats/members/:memberId',
} as const

/** 로그인 후 되돌아갈 경로를 담는다 — `RequireAuth`가 사용한다 */
export function loginPathWithNext(next: string): string {
  return `${paths.login}?next=${encodeURIComponent(next)}`
}

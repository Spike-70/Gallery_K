/**
 * 도메인 상수 — 프런트엔드 아키텍처 문서 §16
 * 12·30 같은 숫자를 화면에 직접 쓰지 않는다.
 */

/** 한 전시의 그림 수 (PRD §4.1) */
export const ARTWORK_COUNT = 12

/** 아카이브 목록 상한 (PRD §6.8) */
export const ARCHIVE_LIMIT = 30

/** 관리자 달력 기본 조회 일수 (API 문서 §9.2) */
export const CALENDAR_DEFAULT_DAYS = 7

/** 관리자 달력 추가 로드 단위 */
export const CALENDAR_PAGE_SIZE = 30

/** 회원 목록 페이지 크기 (API 문서 §9.13) */
export const MEMBER_PAGE_SIZE = 30

/** 열람 기록을 보내기 위한 최소 체류 시간(ms) — 스쳐 지나간 그림은 세지 않는다(프런트 §9.3) */
export const ARTWORK_VIEW_DWELL_MS = 1500

/** 자동 저장 디바운스(ms) — UX 문서 §3.12 */
export const AUTOSAVE_DEBOUNCE_MS = 1200

/** 이미지 처리 폴링 (API 문서 §9.9) */
export const IMAGE_POLL_INTERVAL_MS = 2000
export const IMAGE_POLL_TIMEOUT_MS = 60000

/** 업로드 동시 실행 수 (API 문서 §11.2) */
export const UPLOAD_CONCURRENCY = 3

/** 업로드 제한 (API 문서 §9.8) */
export const UPLOAD_MAX_BYTES = 20 * 1024 * 1024
export const UPLOAD_ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'] as const

/** 입력 길이 제한 — API 문서 §9.4·§9.5 */
export const LIMITS = {
  exhibitionTitle: 20,
  exhibitionTheme: 500,
  artworkTitle: 20,
  artworkArtist: 40,
  artworkYearText: 20,
  artworkDescription: 300,
  artworkCollection: 60,
  artworkSourceUrl: 500,
  memberName: 20,
  noticeBody: 300,
  passwordMin: 8,
  passwordMax: 64,
} as const

/** 설명 권장 길이 — 미달이어도 막지 않고 권한다(UX 문서 §3.14) */
export const ARTWORK_DESCRIPTION_RECOMMENDED = 40

/** 알림 시각 선택 범위 (PRD §6.13) */
export const NOTIFY_HOUR_RANGE = { start: '05:00', end: '11:00', stepMinutes: 30 } as const

/** 제스처 임계값 — UX 문서 §7 */
export const GESTURE = {
  swipeRatio: 0.2,
  swipeVelocity: 0.4,
  dismissDistance: 120,
  dismissVelocity: 0.5,
  longPressMs: 400,
  doubleTapMs: 300,
  zoomMax: 4,
} as const

/** 토스트 지속 시간 — UX 문서 §6 */
export const TOAST_DURATION = { info: 4000, error: 6000 } as const

/** 이미지 지연 로딩 경계 — 상위 6개는 즉시 로드한다(프런트 §9.2) */
export const EAGER_IMAGE_COUNT = 6

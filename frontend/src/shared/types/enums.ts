/**
 * 서버 열거형 미러 — DB 설계서 §5
 * 백엔드 `chalicelib/db/models/enums.py`가 단일 진실 원천이며 이 파일은 그 복사본이다.
 */

export const USER_ROLES = ['viewer', 'curator'] as const
export type UserRole = (typeof USER_ROLES)[number]

export const FONT_SCALES = ['normal', 'large'] as const
export type FontScale = (typeof FONT_SCALES)[number]

export const CREATED_VIA = ['self', 'curator', 'social'] as const
export type CreatedVia = (typeof CREATED_VIA)[number]

/** 소셜 로그인 제공자 (소셜 문서 §6). 백엔드 `SocialProvider`를 미러링한다 */
export const SOCIAL_PROVIDERS = ['kakao', 'google'] as const
export type SocialProvider = (typeof SOCIAL_PROVIDERS)[number]

export const IMAGE_STATUSES = ['empty', 'uploading', 'ready', 'failed'] as const
export type ImageStatus = (typeof IMAGE_STATUSES)[number]

/** DB 컬럼이 아니라 관리자 달력 응답의 파생 상태(Y / ↑ / N) */
export const EXHIBITION_DAY_STATUSES = ['published', 'carried_over', 'empty'] as const
export type ExhibitionDayStatus = (typeof EXHIBITION_DAY_STATUSES)[number]

/** 관리자 달력 2열 버튼의 4가지 모습 (API 문서 §3.9) */
export const EDIT_MODES = ['create', 'edit', 'carry_draft', 'locked'] as const
export type EditMode = (typeof EDIT_MODES)[number]

export const PUSH_PLATFORMS = ['ios', 'android', 'desktop', 'unknown'] as const
export type PushPlatform = (typeof PUSH_PLATFORMS)[number]

export const PUSH_STATUSES = ['active', 'inactive', 'none'] as const
export type PushStatus = (typeof PUSH_STATUSES)[number]

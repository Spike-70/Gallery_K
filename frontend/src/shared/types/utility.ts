/** 공용 유틸리티 타입 */

/** `YYYY-MM-DD` */
export type IsoDate = string
/** RFC 3339 UTC */
export type IsoDateTime = string
/** `HH:MM` (KST) */
export type TimeOfDay = string
/** UUID v4 */
export type Uuid = string

/** 서버 원형(snake_case) 응답에서 값 없음은 항상 `null`이다(API 문서 §2.1). */
export type Nullable<T> = T | null

export type AsyncState = 'idle' | 'loading' | 'success' | 'error'

/** 갤러리 화면이 오늘의 전시인지 아카이브인지 — 컴포넌트 분기의 단일 축(프런트 §5.2) */
export type GalleryMode = 'current' | 'archive' | 'preview'

import type { IsoDateTime } from '@/shared/types/utility'

/** 전역 운영 설정 — API 명세서 §9.17 */
export type AppSetting = {
  key: string
  value: string | number | boolean
  valueType: 'string' | 'number' | 'boolean'
  description: string
  /** 변경할 수 없는 값은 화면에서 읽기 전용으로 그린다 */
  isMutable: boolean
  updatedAt: IsoDateTime | null
}

/** 가입 잠금은 별도 엔드포인트가 아니라 이 키로 조작한다(API 문서 §9.17) */
export const SETTING_KEYS = {
  signupOpen: 'signup_open',
  notifyDefaultHour: 'notify_default_hour',
  notifyCutoffHour: 'notify_cutoff_hour',
  archiveSize: 'archive_size',
} as const

export function settingValue<T>(settings: AppSetting[], key: string, fallback: T): T {
  const found = settings.find((setting) => setting.key === key)
  return (found?.value as T) ?? fallback
}

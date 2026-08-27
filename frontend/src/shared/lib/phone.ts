/**
 * 전화번호 포맷 · 마스킹 — UX 문서 §3.2, API 문서 §6.3
 * 서버 계약은 하이픈 없는 `^01[0-9]{8,9}$`이고, 화면 표시는 하이픈 형식이다.
 */

const DIGITS_ONLY = /\D/g

/** 하이픈·공백을 제거한 순수 숫자 */
export function normalizePhone(value: string): string {
  return value.replace(DIGITS_ONLY, '')
}

/** 입력 중 자동 하이픈: `01012345678` → `010-1234-5678` */
export function formatPhone(value: string): string {
  const digits = normalizePhone(value).slice(0, 11)
  if (digits.length < 4) return digits
  if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  if (digits.length === 10) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
}

/** `010-****-5678` — 관람자 API가 반환하는 마스킹 형식과 동일하게 만든다 */
export function maskPhone(value: string): string {
  const digits = normalizePhone(value)
  if (digits.length < 8) return formatPhone(digits)
  return `${digits.slice(0, 3)}-****-${digits.slice(-4)}`
}

export function isValidPhone(value: string): boolean {
  return /^01[0-9]{8,9}$/.test(normalizePhone(value))
}

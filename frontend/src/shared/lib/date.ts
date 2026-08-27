import type { IsoDate } from '@/shared/types/utility'

/**
 * 날짜 보조 포맷 — 프런트엔드 아키텍처 문서 §2
 *
 * **표시 문자열은 원칙적으로 서버가 준다**(API 문서 §6.1 `today_label`).
 * 이 모듈은 서버 문자열이 없는 자리(관리자 달력 행 등)의 보조 수단이며,
 * 단말 시계로 "오늘"을 판정하지 않는다.
 */

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'] as const

function parse(date: IsoDate): Date {
  // 로컬 타임존 해석 편차를 피하려고 명시적으로 구성한다.
  const [year, month, day] = date.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** `2026. 08. 27. 목` */
export function formatFullDate(date: IsoDate): string {
  const d = parse(date)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}. ${mm}. ${dd}. ${WEEKDAYS[d.getDay()]}`
}

/** `08.27 목` — 관리자 달력 행 */
export function formatShortDate(date: IsoDate): string {
  const d = parse(date)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}.${dd} ${WEEKDAYS[d.getDay()]}`
}

/** `8월 30일 · 토` — 아카이브 행 */
export function formatArchiveDate(date: IsoDate): string {
  const d = parse(date)
  return `${d.getMonth() + 1}월 ${d.getDate()}일 · ${WEEKDAYS[d.getDay()]}`
}

/** `8월 30일` — 연장 라벨 조립용 */
export function formatMonthDay(date: IsoDate): string {
  const d = parse(date)
  return `${d.getMonth() + 1}월 ${d.getDate()}일`
}

/** `2026-08-27` 문자열을 만든다. 서버 `meta.server_date`가 없을 때의 폴백. */
export function toIsoDate(date: Date): IsoDate {
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${mm}-${dd}`
}

/** `from`부터 `days`일간의 날짜 시리즈 (관리자 달력 폴백용) */
export function dateSeries(from: IsoDate, days: number): IsoDate[] {
  const start = parse(from)
  return Array.from({ length: days }, (_, index) => {
    const d = new Date(start)
    d.setDate(start.getDate() + index)
    return toIsoDate(d)
  })
}

/** `HH:MM` 목록 — 알림 시각 선택(30분 단위) */
export function timeOptions(start: string, end: string, stepMinutes: number): string[] {
  const toMinutes = (value: string) => {
    const [h, m] = value.split(':').map(Number)
    return h * 60 + m
  }
  const options: string[] = []
  for (let m = toMinutes(start); m <= toMinutes(end); m += stepMinutes) {
    options.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
  }
  return options
}

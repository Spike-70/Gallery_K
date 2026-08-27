import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * 클래스 병합 — 디자인 시스템 문서 §8.4
 * 외부에서 넘긴 `className`이 컴포넌트 기본값을 이길 수 있게 한다.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

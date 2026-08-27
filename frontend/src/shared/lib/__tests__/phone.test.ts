import { describe, expect, it } from 'vitest'

import { formatPhone, isValidPhone, maskPhone, normalizePhone } from '@/shared/lib/phone'

describe('전화번호 포맷', () => {
  it('입력 중 자동으로 하이픈을 넣는다', () => {
    expect(formatPhone('01012345678')).toBe('010-1234-5678')
    expect(formatPhone('0101234')).toBe('010-1234')
    expect(formatPhone('0212345678')).toBe('021-234-5678')
  })

  it('서버 계약(하이픈 없는 숫자)으로 정규화한다', () => {
    expect(normalizePhone('010-1234-5678')).toBe('01012345678')
  })

  it('관람자 API가 주는 마스킹 형식과 같은 모양을 만든다', () => {
    expect(maskPhone('01012345678')).toBe('010-****-5678')
  })

  it('형식 검증은 서버 정규식과 같은 규칙을 쓴다', () => {
    expect(isValidPhone('010-1234-5678')).toBe(true)
    expect(isValidPhone('02-123-4567')).toBe(false)
  })
})

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LandingPage } from '@/features/landing'
import { EXHIBITION_TITLE, landing } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

/**
 * A 첫 화면은 **데이터 없이도 완전한 레이아웃을 렌더한다**(F-4, PRD §6.1).
 * 이 테스트가 깨지면 "화면 자체는 항상 뜬다"는 계약이 깨진 것이다.
 */
describe('A. 첫 화면', () => {
  it('데이터가 도착하기 전에도 로고와 입장 버튼이 보인다', () => {
    stubApi({ 'GET /public/landing': () => landing() })
    renderWithProviders(<LandingPage />)

    expect(screen.getByRole('heading', { name: 'Morning Gallery K' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '갤러리 입장' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '회원가입' })).toBeInTheDocument()
  })

  it('전시 제목은 비회원에게도 노출된다', async () => {
    stubApi({ 'GET /public/landing': () => landing({ is_authenticated: false }) })
    renderWithProviders(<LandingPage />)

    await waitFor(() => {
      expect(screen.getByText(EXHIBITION_TITLE)).toBeInTheDocument()
    })
  })
})

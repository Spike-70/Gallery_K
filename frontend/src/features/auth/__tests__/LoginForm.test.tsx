import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { LoginPage } from '@/features/auth'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

/**
 * A-1 로그인의 제출 규칙 — UX 설계서 §3.2
 * "두 필드가 채워지면 버튼 활성"은 눈으로만 확인하면 곧 잊힌다.
 */
describe('A-1. 로그인 — 제출 조건', () => {
  it('두 필드가 채워지기 전에는 입장 버튼이 비활성이다', async () => {
    const user = userEvent.setup()
    renderWithProviders(<LoginPage />)

    const submit = screen.getByRole('button', { name: '입장' })
    expect(submit).toHaveAttribute('aria-disabled', 'true')

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    expect(submit).toHaveAttribute('aria-disabled', 'true')

    await user.type(screen.getByLabelText('비밀번호'), 'gallery1234')
    expect(submit).not.toHaveAttribute('aria-disabled', 'true')
  })
})

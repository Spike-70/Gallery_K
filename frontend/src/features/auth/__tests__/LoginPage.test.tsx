import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { useSessionStore } from '@/entities/session/model/sessionStore'
import { LoginPage } from '@/features/auth'
import { sessionUser } from '@/test/fixtures/server'
import { apiError, stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const PHONE = '010-1234-5671'
const PASSWORD = 'gallery-k-2026'

describe('A-1. 로그인', () => {
  beforeEach(() => {
    useSessionStore.setState({ status: 'anonymous', user: null })
  })

  /** 서버는 미가입·차단·오답을 구분하지 않는다(API 문서 §5.2). 스텁도 그 규칙을 지킨다. */
  function stubLogin() {
    return stubApi({
      'POST /auth/login': ({ body }) => {
        const input = body as { phone: string; password: string }
        if (input.password !== PASSWORD) {
          apiError('AUTH_INVALID_CREDENTIALS', '전화번호 또는 비밀번호가 맞지 않습니다.', 401)
        }
        return { user: sessionUser() }
      },
    })
  }

  it('전화번호는 입력 중 자동으로 하이픈이 붙는다', async () => {
    const user = userEvent.setup()
    stubLogin()
    renderWithProviders(<LoginPage />)

    const phone = screen.getByLabelText('전화번호')
    await user.type(phone, '01012345671')

    expect(phone).toHaveValue(PHONE)
  })

  it('자격 증명이 맞지 않으면 폼 상단 배너로 알린다', async () => {
    const user = userEvent.setup()
    stubLogin()
    renderWithProviders(<LoginPage />)

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.type(screen.getByLabelText('비밀번호'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: '입장' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('전화번호 또는 비밀번호가 맞지 않습니다.')
    })
  })

  it('성공하면 세션이 인증 상태로 바뀐다', async () => {
    const user = userEvent.setup()
    stubLogin()
    renderWithProviders(<LoginPage />)

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.type(screen.getByLabelText('비밀번호'), PASSWORD)
    await user.click(screen.getByRole('button', { name: '입장' }))

    await waitFor(() => {
      expect(useSessionStore.getState().status).toBe('authenticated')
    })
  })
})

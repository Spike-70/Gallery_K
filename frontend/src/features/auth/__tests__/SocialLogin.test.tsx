import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { useSessionStore } from '@/entities/session/model/sessionStore'
import { LoginPage, SocialLinkPage } from '@/features/auth'
import { sessionUser, socialProvider } from '@/test/fixtures/server'
import { apiError, stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const PROVIDERS = 'GET /auth/social/providers'

describe('A-1. 소셜 로그인 버튼', () => {
  beforeEach(() => {
    useSessionStore.setState({ status: 'anonymous', user: null })
  })

  it('켜진 제공자만 버튼으로 나온다', async () => {
    stubApi({
      [PROVIDERS]: () => ({
        providers: [socialProvider(), socialProvider({ provider: 'google', label: '구글' })],
      }),
    })
    renderWithProviders(<LoginPage />)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '카카오로 시작하기' })).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: '구글로 시작하기' })).toBeInTheDocument()
  })

  it('버튼은 링크다 — 자바스크립트 없이도 이동한다 (UX §3.2)', async () => {
    stubApi({ [PROVIDERS]: () => ({ providers: [socialProvider()] }) })
    renderWithProviders(<LoginPage />)

    const link = await screen.findByRole('link', { name: '카카오로 시작하기' })
    // 라우터 경로가 아니라 서버로 나가는 절대 경로여야 리다이렉트 방식이 성립한다.
    expect(link).toHaveAttribute(
      'href',
      `/api/auth/social/kakao/start?next=${encodeURIComponent('/gallery')}`,
    )
  })

  it('제공자가 없으면 구분선까지 그리지 않는다', async () => {
    stubApi({ [PROVIDERS]: () => ({ providers: [] }) })
    renderWithProviders(<LoginPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '입장' })).toBeInTheDocument()
    })
    expect(screen.queryByText('또는')).not.toBeInTheDocument()
  })

  it('콜백 실패 코드를 한국어 배너로 옮긴다', async () => {
    stubApi({ [PROVIDERS]: () => ({ providers: [socialProvider()] }) })
    renderWithProviders(<LoginPage />, { route: '/login?social_error=SOCIAL_STATE_INVALID' })

    expect(screen.getByRole('alert')).toHaveTextContent(
      '로그인 요청이 만료되었습니다. 처음부터 다시 시도해 주세요.',
    )
  })

  it('사용자가 동의를 취소하면 아무 것도 띄우지 않는다', async () => {
    stubApi({ [PROVIDERS]: () => ({ providers: [socialProvider()] }) })
    renderWithProviders(<LoginPage />, { route: '/login' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('로그인 후 돌아갈 곳을 소셜 링크에도 실어 보낸다', async () => {
    stubApi({ [PROVIDERS]: () => ({ providers: [socialProvider()] }) })
    renderWithProviders(<LoginPage />, { route: '/login?next=%2Farchive' })

    const link = await screen.findByRole('link', { name: '카카오로 시작하기' })
    expect(link).toHaveAttribute(
      'href',
      `/api/auth/social/kakao/start?next=${encodeURIComponent('/archive')}`,
    )
  })
})

describe('A-4. 계정 연결', () => {
  beforeEach(() => {
    useSessionStore.setState({ status: 'anonymous', user: null })
  })

  it('기본은 기존 계정 연결이다 — 전화번호와 비밀번호를 받는다', async () => {
    stubApi({})
    renderWithProviders(<SocialLinkPage />, { route: '/auth/link' })

    expect(screen.getByLabelText('전화번호')).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '연결하기' })).toBeInTheDocument()
  })

  it('모드를 바꿔도 입력한 전화번호는 남는다', async () => {
    const user = userEvent.setup()
    stubApi({})
    renderWithProviders(<SocialLinkPage />, { route: '/auth/link' })

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.click(screen.getByRole('button', { name: '처음이신가요? 새로 시작하기' }))

    expect(screen.getByLabelText('전화번호')).toHaveValue('010-1234-5671')
    // 신규 모드에는 비밀번호를 받지 않는다 — 소셜이 곧 로그인 수단이다.
    expect(screen.queryByLabelText('비밀번호')).not.toBeInTheDocument()
    expect(screen.getByLabelText('이름')).toBeInTheDocument()
  })

  it('연결에 성공하면 세션이 인증 상태가 된다', async () => {
    const user = userEvent.setup()
    stubApi({ 'POST /auth/social/link': () => ({ user: sessionUser() }) })
    renderWithProviders(<SocialLinkPage />, { route: '/auth/link' })

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.type(screen.getByLabelText('비밀번호'), 'password123')
    await user.click(screen.getByRole('button', { name: '연결하기' }))

    await waitFor(() => {
      expect(useSessionStore.getState().status).toBe('authenticated')
    })
  })

  it('미가입·비밀번호 불일치를 구분하지 않는다 (§5.2)', async () => {
    const user = userEvent.setup()
    stubApi({
      'POST /auth/social/link': () =>
        apiError('AUTH_INVALID_CREDENTIALS', '전화번호 또는 비밀번호가 맞지 않습니다.', 401),
    })
    renderWithProviders(<SocialLinkPage />, { route: '/auth/link' })

    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.type(screen.getByLabelText('비밀번호'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: '연결하기' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        '전화번호 또는 비밀번호가 맞지 않습니다.',
      )
    })
  })

  it('신규 모드에서 가입된 번호면 연결 모드로 가는 길을 연다', async () => {
    const user = userEvent.setup()
    stubApi({
      'POST /auth/social/signup': () =>
        apiError('SIGNUP_PHONE_TAKEN', '이미 가입된 번호입니다.', 409),
    })
    renderWithProviders(<SocialLinkPage />, { route: '/auth/link' })

    await user.click(screen.getByRole('button', { name: '처음이신가요? 새로 시작하기' }))
    await user.type(screen.getByLabelText('전화번호'), '01012345671')
    await user.type(screen.getByLabelText('이름'), '관람자')
    await user.click(screen.getByLabelText(/서비스 이용과 개인정보 처리에 동의/))
    await user.click(screen.getByRole('button', { name: '시작하기' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('이미 가입된 번호입니다.')
    })
    // 막다른 오류에 길을 하나 연다 — 배너 안의 전환 링크.
    expect(
      screen.getByRole('alert').querySelector('button'),
    ).toHaveTextContent('이미 회원이신가요? 기존 계정에 연결하기')
  })
})

import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SocialSection } from '@/features/settings/components/SocialSection'
import { socialIdentity, socialProvider } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const IDENTITIES = 'GET /me/social-identities'
const PROVIDERS = 'GET /auth/social/providers'

describe('C-4. 연결된 로그인', () => {
  it('연결된 제공자는 목록에, 나머지는 연결 버튼으로 나온다', async () => {
    stubApi({
      [IDENTITIES]: () => ({ identities: [socialIdentity()], can_unlink: true }),
      [PROVIDERS]: () => ({
        providers: [socialProvider(), socialProvider({ provider: 'google', label: '구글' })],
      }),
    })
    renderWithProviders(<SocialSection />)

    expect(await screen.findByText('카카오 연결됨')).toBeInTheDocument()
    // 제공자 목록은 별도 요청이다. 그것이 도착한 뒤에 부재를 단정해야 의미가 있다.
    expect(await screen.findByRole('link', { name: '구글 연결하기' })).toBeInTheDocument()
    // 이미 연결된 카카오는 연결 버튼으로 다시 나오지 않는다.
    expect(screen.queryByRole('link', { name: '카카오 연결하기' })).not.toBeInTheDocument()
  })

  it('연결 버튼은 설정 화면으로 돌아온다', async () => {
    stubApi({
      [IDENTITIES]: () => ({ identities: [], can_unlink: true }),
      [PROVIDERS]: () => ({ providers: [socialProvider()] }),
    })
    renderWithProviders(<SocialSection />)

    const link = await screen.findByRole('link', { name: '카카오 연결하기' })
    expect(link).toHaveAttribute(
      'href',
      `/api/auth/social/kakao/start?next=${encodeURIComponent('/settings')}`,
    )
  })

  it('마지막 로그인 수단이면 해제를 막고 이유를 알려준다', async () => {
    stubApi({
      [IDENTITIES]: () => ({ identities: [socialIdentity()], can_unlink: false }),
      [PROVIDERS]: () => ({ providers: [socialProvider()] }),
    })
    renderWithProviders(<SocialSection />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '해제' })).toBeDisabled()
    })
    expect(screen.getByText('마지막 로그인 수단은 해제할 수 없습니다.')).toBeInTheDocument()
  })
})

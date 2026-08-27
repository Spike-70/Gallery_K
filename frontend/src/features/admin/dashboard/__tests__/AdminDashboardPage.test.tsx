import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AdminDashboardPage } from '@/features/admin/dashboard'
import { TODAY, TOMORROW, adminDay, adminSummary } from '@/test/fixtures/server'
import { paged, stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('B. 관리자 홈', () => {
  function stubDashboard() {
    return stubApi({
      'GET /admin/summary': () => adminSummary({ today_entrant_count: 14, weekly_active_ratio: 62 }),
      'GET /admin/exhibitions/calendar': () =>
        paged(
          {
            days: [
              // 오늘은 발행됨(Y)
              adminDay(TODAY, {
                status: 'published',
                title: '빛을 등진 사람들',
                edit_mode: 'edit',
              }),
              // 내일은 드래프트만 있으므로 준비 안 됨(N)
              adminDay(TOMORROW, {
                has_draft: true,
                draft_progress: {
                  artwork_count: 4,
                  complete_artwork_count: 4,
                  has_title: true,
                  has_theme: false,
                },
              }),
            ],
          },
          { limit: 7, count: 2 },
        ),
    })
  }

  it('오늘을 맨 위로 하는 날짜 목록을 보여준다', async () => {
    stubDashboard()
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      expect(screen.getByText(/^오늘 · /)).toBeInTheDocument()
    })
  })

  it('발행 상태를 문자로도 표기한다 (DS-5 — 색만으로 말하지 않는다)', async () => {
    stubDashboard()
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      expect(screen.getAllByText('Y').length).toBeGreaterThan(0)
      expect(screen.getAllByText('N').length).toBeGreaterThan(0)
    })
  })

  it('요약 줄이 오늘 입장 수와 주간 비율을 함께 보여준다', async () => {
    stubDashboard()
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      expect(screen.getByText(/오늘 입장 \d+명 · 이번 주 꾸준히 보는 분 \d+%/)).toBeInTheDocument()
    })
  })
})

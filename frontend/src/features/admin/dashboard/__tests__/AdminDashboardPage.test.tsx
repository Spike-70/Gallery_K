import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { AdminDashboardPage } from '@/features/admin/dashboard'
import { db, resetDb } from '@/mocks/db'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('B. 관리자 홈', () => {
  beforeEach(() => {
    resetDb()
    db.currentUserId = db.members[0].id // 큐레이터
  })

  it('오늘을 맨 위로 하는 날짜 목록을 보여준다', async () => {
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      expect(screen.getByText(/^오늘 · /)).toBeInTheDocument()
    })
  })

  it('발행 상태를 문자로도 표기한다 (DS-5 — 색만으로 말하지 않는다)', async () => {
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      // 오늘은 발행됨(Y), 내일은 드래프트만 있으므로 준비 안 됨(N)
      expect(screen.getAllByText('Y').length).toBeGreaterThan(0)
      expect(screen.getAllByText('N').length).toBeGreaterThan(0)
    })
  })

  it('요약 줄이 오늘 입장 수와 주간 비율을 함께 보여준다', async () => {
    renderWithProviders(<AdminDashboardPage />, { route: '/admin' })

    await waitFor(() => {
      expect(screen.getByText(/오늘 입장 \d+명 · 이번 주 꾸준히 보는 분 \d+%/)).toBeInTheDocument()
    })
  })
})

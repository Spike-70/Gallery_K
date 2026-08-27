import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { GalleryPage } from '@/features/gallery'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { db, resetDb } from '@/mocks/db'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('C. 갤러리', () => {
  beforeEach(() => {
    resetDb()
    // 목 서버 쪽 세션을 세운다. 화면은 쿠키 유무를 알지 못한다.
    db.currentUserId = db.members[1].id
    sessionStorage.clear()
  })

  it('12점의 썸네일을 그리드로 보여준다', async () => {
    renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('빛을 등진 사람들')
    })

    const thumbs = screen.getAllByRole('listitem')
    expect(thumbs).toHaveLength(ARTWORK_COUNT)
  })

  it('하단에 되돌아갈 길이 항상 보인다 (UX-3)', async () => {
    renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '지난 전시' })).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: '설정' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '첫 화면으로' })).toBeInTheDocument()
  })

  it('입장 기록은 세션당 날짜별로 한 번만 전송된다 (§9.3)', async () => {
    renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(db.enteredDates.has(db.today)).toBe(true)
    })
  })
})

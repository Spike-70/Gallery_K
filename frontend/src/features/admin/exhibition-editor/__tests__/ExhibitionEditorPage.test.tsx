import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'

import { ExhibitionEditorPage } from '@/features/admin/exhibition-editor'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { db, resetDb, shiftDate } from '@/mocks/db'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('B-2. 업로드 화면', () => {
  beforeEach(() => {
    resetDb()
    db.currentUserId = db.members[0].id
  })

  it('빈 전시에도 12칸이 항상 렌더된다 (API §9.3 계약)', async () => {
    const emptyDate = shiftDate(new Date(db.today), 5)

    renderWithProviders(
      <Routes>
        <Route path="/admin/exhibitions/:date" element={<ExhibitionEditorPage />} />
      </Routes>,
      { route: `/admin/exhibitions/${emptyDate}` },
    )

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(ARTWORK_COUNT)
    })
  })

  it('발행 조건이 남아 있으면 무엇이 부족한지 알려준다', async () => {
    const emptyDate = shiftDate(new Date(db.today), 5)

    renderWithProviders(
      <Routes>
        <Route path="/admin/exhibitions/:date" element={<ExhibitionEditorPage />} />
      </Routes>,
      { route: `/admin/exhibitions/${emptyDate}` },
    )

    await waitFor(() => {
      expect(screen.getByText(/^발행까지 — /)).toHaveTextContent('전시 제목')
    })
  })
})

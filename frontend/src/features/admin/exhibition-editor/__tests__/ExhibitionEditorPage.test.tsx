import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { ExhibitionEditorPage } from '@/features/admin/exhibition-editor'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { adminExhibition } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const EMPTY_DATE = '2026-09-02'

describe('B-2. 업로드 화면', () => {
  function renderEditor() {
    stubApi({
      'GET /admin/exhibitions/{date}': ({ params }) => adminExhibition(params.date),
    })

    return renderWithProviders(
      <Routes>
        <Route path="/admin/exhibitions/:date" element={<ExhibitionEditorPage />} />
      </Routes>,
      { route: `/admin/exhibitions/${EMPTY_DATE}` },
    )
  }

  it('빈 전시에도 12칸이 항상 렌더된다 (API §9.3 계약)', async () => {
    renderEditor()

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(ARTWORK_COUNT)
    })
  })

  it('발행 조건이 남아 있으면 무엇이 부족한지 알려준다', async () => {
    renderEditor()

    await waitFor(() => {
      expect(screen.getByText(/^발행까지 — /)).toHaveTextContent('전시 제목')
    })
  })
})

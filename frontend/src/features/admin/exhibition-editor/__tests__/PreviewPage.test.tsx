import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { PreviewPage } from '@/features/admin/exhibition-editor'
import { currentExhibition, pendingArtwork } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const DATE = '2026-08-28'

/**
 * 미리보기는 **미완성 전시를 그대로 보여준다**(API 문서 §9.12). 아직 `ready`가 아닌
 * 슬롯은 서버가 `image: null`을 주고 화면이 자리표시자를 그린다.
 *
 * 이 검사가 없던 동안 프런트 타입이 `image`를 non-nullable로 선언하고 있었고,
 * 매퍼가 `toImageSet(null)`에서 터져 **미리보기 화면 전체가 죽었다.**
 */
describe('미리보기 — 이미지가 아직 없는 슬롯', () => {
  function renderPreview() {
    stubApi({
      'GET /admin/exhibitions/{date}/preview': () =>
        currentExhibition({
          artworks: [pendingArtwork(1), ...Array.from({ length: 11 }, (_, i) => pendingArtwork(i + 2))],
        }),
    })
    return renderWithProviders(
      <Routes>
        <Route path="/admin/exhibitions/:date/preview" element={<PreviewPage />} />
      </Routes>,
      { route: `/admin/exhibitions/${DATE}/preview` },
    )
  }

  it('화면이 죽지 않고 자리표시자를 그린다', async () => {
    renderPreview()

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(12)
    })
    // 오류가 아니라 '아직 없음'이므로 재시도를 권하지 않는다.
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument()
  })

  it('없는 그림에 확대 조작을 붙이지 않는다', async () => {
    renderPreview()

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(12)
    })
    expect(screen.queryByRole('button', { name: /크게 보기/ })).not.toBeInTheDocument()
  })
})

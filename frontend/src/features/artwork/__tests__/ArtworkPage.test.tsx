import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { ArtworkPage } from '@/features/artwork'
import { artworkDetail, artworkId } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('C-2. 그림', () => {
  /** 경로 변수로 온 id에서 자리 번호를 되찾는다. 픽스처의 id 규칙과 짝을 이룬다. */
  function positionOf(id: string): number {
    return Number(id.split('-').at(-1))
  }

  function renderArtwork(position: number) {
    stubApi({
      'GET /artworks/{artworkId}': ({ params }) => artworkDetail(positionOf(params.artworkId)),
      'POST /artworks/{artworkId}/view': () => ({ viewed_artwork_count: 1 }),
    })

    return renderWithProviders(
      <Routes>
        <Route path="/gallery/artworks/:artworkId" element={<ArtworkPage />} />
      </Routes>,
      { route: `/gallery/artworks/${artworkId(position)}` },
    )
  }

  it('제목·작가·설명이 그림보다 먼저 보인다 (U-1)', async () => {
    renderArtwork(1)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('그림 1')
    })
    expect(screen.getByText(/작가 1/)).toBeInTheDocument()
  })

  it('첫 그림에는 이전 링크가 없고 다음 링크만 있다 (UX-2 — 순환하지 않는다)', async () => {
    renderArtwork(1)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '다음 그림 →' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('link', { name: '← 이전 그림' })).not.toBeInTheDocument()
  })

  it('제스처를 모르는 사용자를 위해 크게 보기 버튼이 항상 있다 (UX-7)', async () => {
    renderArtwork(1)

    await waitFor(() => {
      expect(screen.getAllByText('크게 보기').length).toBeGreaterThan(0)
    })
  })

  it('되돌아갈 길은 오늘의 갤러리다', async () => {
    renderArtwork(1)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '갤러리 화면으로' })).toHaveAttribute('href', '/gallery')
    })
  })
})

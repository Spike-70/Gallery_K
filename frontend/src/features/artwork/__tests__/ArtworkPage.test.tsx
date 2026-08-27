import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'

import { ArtworkPage } from '@/features/artwork'
import { currentExhibition, db, resetDb } from '@/mocks/db'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('C-2. 그림', () => {
  beforeEach(() => {
    resetDb()
    db.currentUserId = db.members[1].id
  })

  function renderArtwork(artworkId: string) {
    return renderWithProviders(
      <Routes>
        <Route path="/gallery/artworks/:artworkId" element={<ArtworkPage />} />
      </Routes>,
      { route: `/gallery/artworks/${artworkId}` },
    )
  }

  function firstSlot() {
    const exhibition = currentExhibition()
    if (!exhibition) throw new Error('현재 전시가 없습니다')
    return exhibition.slots[0]
  }

  it('제목·작가·설명이 그림보다 먼저 보인다 (U-1)', async () => {
    const first = firstSlot()
    renderArtwork(first.artworkId as string)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(first.title as string)
    })
    expect(screen.getByText(new RegExp(first.artist as string))).toBeInTheDocument()
  })

  it('첫 그림에는 이전 링크가 없고 다음 링크만 있다 (UX-2 — 순환하지 않는다)', async () => {
    renderArtwork(firstSlot().artworkId as string)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '다음 그림 →' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('link', { name: '← 이전 그림' })).not.toBeInTheDocument()
  })

  it('제스처를 모르는 사용자를 위해 크게 보기 버튼이 항상 있다 (UX-7)', async () => {
    renderArtwork(firstSlot().artworkId as string)

    await waitFor(() => {
      expect(screen.getAllByText('크게 보기').length).toBeGreaterThan(0)
    })
  })

  it('되돌아갈 길은 오늘의 갤러리다', async () => {
    renderArtwork(firstSlot().artworkId as string)

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '갤러리 화면으로' })).toHaveAttribute('href', '/gallery')
    })
  })
})

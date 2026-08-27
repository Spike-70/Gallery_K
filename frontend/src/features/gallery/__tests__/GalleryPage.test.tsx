import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { GalleryPage } from '@/features/gallery'
import { ARTWORK_COUNT } from '@/shared/config/constants'
import { EXHIBITION_TITLE, currentExhibition } from '@/test/fixtures/server'
import { stubApi } from '@/test/utils/apiStub'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

const ENTRY_LOG = 'POST /exhibitions/{date}/view'

describe('C. 갤러리', () => {
  beforeEach(() => {
    // 입장 기록 마커는 세션에 남는다. 테스트끼리 옮겨 다니지 않게 비운다(§9.3).
    sessionStorage.clear()
  })

  function stubGallery() {
    return stubApi({
      'GET /exhibitions/current': () => currentExhibition(),
      [ENTRY_LOG]: () => ({ recorded: true }),
      'GET /artworks/{artworkId}': () => ({}),
    })
  }

  it('12점의 썸네일을 그리드로 보여준다', async () => {
    stubGallery()
    renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(EXHIBITION_TITLE)
    })

    expect(screen.getAllByRole('listitem')).toHaveLength(ARTWORK_COUNT)
  })

  it('하단에 되돌아갈 길이 항상 보인다 (UX-3)', async () => {
    stubGallery()
    renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(screen.getByRole('link', { name: '지난 전시' })).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: '설정' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '첫 화면으로' })).toBeInTheDocument()
  })

  it('입장 기록은 세션당 날짜별로 한 번만 전송된다 (§9.3)', async () => {
    const api = stubGallery()
    const { unmount } = renderWithProviders(<GalleryPage />, { route: '/gallery' })

    await waitFor(() => {
      expect(api.called(ENTRY_LOG)).toBe(true)
    })
    unmount()

    // 같은 세션에서 다시 열어도 두 번째 요청은 나가지 않는다.
    renderWithProviders(<GalleryPage />, { route: '/gallery' })
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(EXHIBITION_TITLE)
    })
    expect(api.callsFor(ENTRY_LOG)).toHaveLength(1)
  })
})

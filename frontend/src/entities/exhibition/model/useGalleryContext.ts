import { useMemo } from 'react'
import { useParams } from 'react-router-dom'

import { actions } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import type { GalleryMode, IsoDate, Uuid } from '@/shared/types/utility'

/**
 * 갤러리 문맥 — 프런트엔드 아키텍처 문서 §5.2
 *
 * `/gallery`와 `/archive/:date`는 **같은 컴포넌트를 재사용**한다. 차이는 데이터 소스와
 * 상단 안내 배너뿐이다. 그림 화면도 같은 원리로 두 경로를 갖는다.
 *
 * **되돌아가기 대상은 이 훅이 현재 라우트에서 파생한다.** 컴포넌트가 문맥을 직접
 * 판단하지 않는다 — 판단이 흩어지면 아카이브에서 연 그림이 오늘의 전시로 튕긴다(F-14).
 *
 * 위치가 `entities`인 이유 — 갤러리(C)와 그림(C-2) **두 기능이 같은 문맥 규칙**을 쓴다.
 * 기능 간 상호 참조는 금지되므로 공유 개념은 한 계층 위로 올린다(프런트 §3.1).
 */
export type GalleryContext = {
  mode: GalleryMode
  /** 아카이브 모드일 때의 발행일 */
  date: IsoDate | null
  /** 이 문맥의 갤러리 화면 경로 */
  galleryPath: string
  /** 이 문맥의 전시 테마 경로 */
  themePath: string
  /** 이 문맥의 그림 경로 */
  artworkPath: (artworkId: Uuid) => string
  /** 갤러리로 돌아가는 링크 문구 — 아카이브에서는 `이 전시로` */
  backToGalleryLabel: string
}

export function useGalleryContext(): GalleryContext {
  const { date } = useParams<{ date?: IsoDate }>()

  return useMemo(() => {
    if (date) {
      return {
        mode: 'archive' as const,
        date,
        galleryPath: paths.archiveDate(date),
        themePath: paths.archiveTheme(date),
        artworkPath: (artworkId: Uuid) => paths.archiveArtwork(date, artworkId),
        backToGalleryLabel: actions.backThisExhibition,
      }
    }
    return {
      mode: 'current' as const,
      date: null,
      galleryPath: paths.gallery,
      themePath: paths.galleryTheme,
      artworkPath: (artworkId: Uuid) => paths.galleryArtwork(artworkId),
      backToGalleryLabel: actions.backGallery,
    }
  }, [date])
}

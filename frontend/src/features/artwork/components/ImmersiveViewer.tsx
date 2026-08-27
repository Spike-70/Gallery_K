import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import type { ArtworkDetail } from '@/entities/artwork/model/types'
import { artworkAltText } from '@/entities/artwork/model/types'
import { usePinchZoom } from '@/features/artwork/hooks/usePinchZoom'
import { actions, status } from '@/shared/config/messages'
import { useFocusTrap } from '@/shared/hooks/useFocusTrap'
import { useLockBodyScroll } from '@/shared/hooks/useLockBodyScroll'
import { useSwipe } from '@/shared/hooks/useSwipe'
import { STORAGE_KEYS, localStore } from '@/shared/lib/storage'
import { IconButton, Spinner } from '@/shared/ui'

/**
 * 전체화면 뷰어 — UX 설계서 §3.8, 디자인 시스템 §8.2
 *
 * 검은 배경 · 모든 UI 제거 · 핀치 줌(최대 4배) · 더블탭 2배 · 확대 상태 패닝 ·
 * 아래로 스와이프/`×`/`Esc`로 닫기.
 *
 * 원본 이미지는 **확대 제스처가 시작될 때만** 로드한다. 그전에는 display를 보여준다(§9.2).
 * 힌트는 최초 1회만 2초 노출한다.
 *
 * 색은 `.gk-immersive` 스코프에서 토큰 값만 교체된다 — 컴포넌트에 다크 분기가 없다(§2.2).
 */
export type ImmersiveViewerProps = {
  artwork: ArtworkDetail
  onClose: () => void
}

export function ImmersiveViewer({ artwork, onClose }: ImmersiveViewerProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const { zoom, isZoomed, toggleZoom, handlers: zoomHandlers } = usePinchZoom()
  const [showHint, setShowHint] = useState(() => localStore.get(STORAGE_KEYS.zoomHintSeen) !== '1')

  useLockBodyScroll(true)
  useFocusTrap(panelRef, true)

  const swipe = useSwipe({
    horizontal: false,
    vertical: true,
    onSwipe: (direction) => {
      if (direction === 'down' && !isZoomed) onClose()
    },
  })

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  useEffect(() => {
    if (!showHint) return
    localStore.set(STORAGE_KEYS.zoomHintSeen, '1')
    const timer = window.setTimeout(() => setShowHint(false), 2000)
    return () => window.clearTimeout(timer)
  }, [showHint])

  /**
   * 확대가 시작된 뒤에만 원본을 건다. 그전에는 display 이미지가 보인다(§9.2).
   *
   * **`src`를 바로 갈아끼우지 않는다.** 원본은 수 MB라 교체 순간 화면이 비고,
   * 사용자는 아무 표시 없이 기다리게 된다. 뒤에서 받아 두었다가 **로드된 뒤에** 바꾸고,
   * 받는 동안에는 우상단에 작은 스피너를 띄운다(UX §3.8 상태표).
   */
  const originUrl = artwork.image.originUrl
  const [originReady, setOriginReady] = useState(false)
  const [originLoading, setOriginLoading] = useState(false)

  useEffect(() => {
    if (!isZoomed || !originUrl || originReady || originLoading) return
    setOriginLoading(true)
    const image = new Image()
    image.src = originUrl
    const settle = () => setOriginLoading(false)
    image.onload = () => {
      setOriginReady(true)
      settle()
    }
    image.onerror = settle
  }, [isZoomed, originUrl, originReady, originLoading])

  const source = originReady && originUrl ? originUrl : artwork.image.displayUrl

  return createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label={artworkAltText(artwork)}
      className="gk-immersive fixed inset-0 z-immersive flex items-center justify-center bg-canvas"
      onPointerDown={(event) => {
        zoomHandlers.onPointerDown(event)
        if (!isZoomed) swipe.handlers.onPointerDown(event)
      }}
      onPointerMove={(event) => {
        zoomHandlers.onPointerMove(event)
        if (!isZoomed) swipe.handlers.onPointerMove(event)
      }}
      onPointerUp={(event) => {
        zoomHandlers.onPointerUp(event)
        if (!isZoomed) swipe.handlers.onPointerUp(event)
      }}
      onPointerCancel={zoomHandlers.onPointerCancel}
    >
      <div className="absolute right-2 top-2 z-immersive flex items-center gap-1">
        {originLoading ? <Spinner size="sm" label={status.loading} /> : null}
        {/*
          핀치를 모르는 사용자를 위한 확대 대체 수단(UX-7). 제스처만 있는 기능은 두지 않는다.
        */}
        <IconButton
          icon="zoom-in"
          label={isZoomed ? actions.zoomOut : actions.zoomIn}
          tone="inverse"
          iconSize="lg"
          aria-pressed={isZoomed}
          onClick={toggleZoom}
        />
        <IconButton icon="close" label={actions.close} tone="inverse" iconSize="lg" onClick={onClose} />
      </div>

      <img
        src={source}
        alt={artworkAltText(artwork)}
        draggable={false}
        className="max-h-full max-w-full select-none touch-none object-contain"
        style={{
          // 인라인 style은 확대/이동 transform에 한해 허용된다(디자인 시스템 §11.4).
          transform: `translate(${zoom.x + swipe.offset.x}px, ${zoom.y + swipe.offset.y}px) scale(${zoom.scale})`,
          transition: swipe.dragging ? 'none' : 'transform var(--gk-duration-base) var(--gk-ease-standard)',
        }}
      />

      {showHint ? (
        <p className="absolute bottom-8 text-caption text-secondary">{status.zoomHint}</p>
      ) : null}
    </div>,
    document.body,
  )
}

import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * 라우트 전환 접근성 — 프런트엔드 아키텍처 문서 §11
 *
 * SPA는 화면을 바꿔도 브라우저가 아무것도 알리지 않는다. 스크린리더 사용자는 링크를
 * 누른 뒤 **자기가 어디에 있는지 모른 채** 이전 화면의 포커스 자리에 남는다.
 *
 * 두 가지를 한다.
 *  1. 메인 랜드마크로 포커스를 옮긴다 — 다음 `Tab`이 새 화면의 처음에서 시작한다.
 *  2. 새 화면의 제목을 `aria-live`로 읽어 준다.
 *
 * **첫 진입에서는 하지 않는다.** 페이지를 막 연 사람에게 제목을 다시 읽어 줄 이유가 없다.
 */
export function RouteAnnouncer() {
  const { pathname } = useLocation()
  const [announcement, setAnnouncement] = useState('')
  const firstRender = useRef(true)

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }

    const main = document.getElementById('gk-main')
    main?.focus({ preventScroll: true })

    // 제목은 화면이 그린 `h1`에서 가져온다. 경로별 이름표를 따로 두면 곧 어긋난다.
    const heading = document.querySelector('#gk-main h1')?.textContent?.trim()
    setAnnouncement(heading || document.title)
  }, [pathname])

  return (
    <p aria-live="polite" aria-atomic="true" className="gk-sr-only">
      {announcement}
    </p>
  )
}

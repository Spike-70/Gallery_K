import { Outlet } from 'react-router-dom'

/** 단독 화면(A · A-1 · D · 미리보기 · 오류)의 레이아웃 */
export function PlainLayout() {
  return (
    <main id="gk-main" tabIndex={-1} className="min-h-screen focus:outline-none">
      <Outlet />
    </main>
  )
}

import { createBrowserRouter } from 'react-router-dom'

import { GalleryLayout } from '@/app/layouts/GalleryLayout'
import { PlainLayout } from '@/app/layouts/PlainLayout'
import { StudioLayout } from '@/app/layouts/StudioLayout'
import { RedirectIfAuthed, RequireAuth, RequireCurator } from '@/app/router/guards'
import { lazyRoute } from '@/app/router/lazyRoute'
import { paths, routePatterns } from '@/app/router/paths'
import { shouldPrefetch } from '@/shared/lib/platform'

import { LandingPage } from '@/features/landing'
import { GalleryPage } from '@/features/gallery'
import { ArtworkPage } from '@/features/artwork'
import { NotFoundPage, RouteErrorPage } from '@/features/errors'

/**
 * 라우트 트리 — 프런트엔드 아키텍처 문서 §5
 *
 * 청크 예산(§5.4)을 코드로 표현한다.
 *  - 초기 번들: 셸 · A · A-1 · C · C-2
 *  - 지연 로드: D · 재설정 · C-1 · C-3 · C-4
 *  - **관리자 청크는 `RequireCurator` 아래에서만 `lazy()`로 참조한다.**
 *    관람자 경로에서 절대 로드되지 않는다(F-8).
 *
 * `lazy()`의 대상만 default export를 쓴다(코딩 규약 §16).
 */

/**
 * 인증 화면은 한 기능 폴더(= 하나의 공개 표면)를 공유하므로 통째로 지연 로드한다.
 * 대신 A 첫 화면이 뜬 뒤 유휴 시간에 이 청크를 미리 받아 A-1 진입을 즉시로 만든다(§9.4).
 */
const LoginPage = lazyRoute(() =>
  import('@/features/auth').then((module) => ({ default: module.LoginPage })),
)
const SignupPage = lazyRoute(() =>
  import('@/features/auth').then((module) => ({ default: module.SignupPage })),
)
const PasswordResetPage = lazyRoute(() =>
  import('@/features/auth').then((module) => ({ default: module.PasswordResetPage })),
)
const PasswordChangePage = lazyRoute(() =>
  import('@/features/auth').then((module) => ({ default: module.PasswordChangePage })),
)
const ExhibitionThemePage = lazyRoute(() =>
  import('@/features/exhibition-theme').then((module) => ({ default: module.ExhibitionThemePage })),
)
const ArchivePage = lazyRoute(() =>
  import('@/features/archive').then((module) => ({ default: module.ArchivePage })),
)
const SettingsPage = lazyRoute(() =>
  import('@/features/settings').then((module) => ({ default: module.SettingsPage })),
)

// 지연 로드 — 관리자(admin 청크)
const AdminDashboardPage = lazyRoute(() =>
  import('@/features/admin/dashboard').then((module) => ({ default: module.AdminDashboardPage })),
)
const ExhibitionEditorPage = lazyRoute(() =>
  import('@/features/admin/exhibition-editor').then((module) => ({ default: module.ExhibitionEditorPage })),
)
const ThemeEditorPage = lazyRoute(() =>
  import('@/features/admin/exhibition-editor').then((module) => ({ default: module.ThemeEditorPage })),
)
const ArtworkEditorPage = lazyRoute(() =>
  import('@/features/admin/exhibition-editor').then((module) => ({ default: module.ArtworkEditorPage })),
)
const PreviewPage = lazyRoute(() =>
  import('@/features/admin/exhibition-editor').then((module) => ({ default: module.PreviewPage })),
)
const MembersPage = lazyRoute(() =>
  import('@/features/admin/members').then((module) => ({ default: module.MembersPage })),
)
const AdminSettingsPage = lazyRoute(() =>
  import('@/features/admin/settings').then((module) => ({ default: module.AdminSettingsPage })),
)
const StatsPage = lazyRoute(() =>
  import('@/features/admin/stats').then((module) => ({ default: module.StatsPage })),
)
const MemberStatsPage = lazyRoute(() =>
  import('@/features/admin/stats').then((module) => ({ default: module.MemberStatsPage })),
)

/** 첫 화면 렌더 후 유휴 시간에 인증 청크를 미리 받는다. 데이터 절약 모드면 하지 않는다. */
export function prefetchAuthChunk(): void {
  if (!shouldPrefetch()) return
  const request = window.requestIdleCallback ?? ((callback: () => void) => window.setTimeout(callback, 1200))
  request(() => void import('@/features/auth'))
}

export const router = createBrowserRouter([
  {
    errorElement: <RouteErrorPage />,
    children: [
      // ── 단독 화면 ────────────────────────────────────────────────────
      {
        element: <PlainLayout />,
        children: [
          { path: paths.landing, element: <LandingPage /> },
          {
            path: paths.login,
            element: (
              <RedirectIfAuthed>
                <LoginPage />
              </RedirectIfAuthed>
            ),
          },
          {
            path: paths.signup,
            element: (
              <RedirectIfAuthed>
                <SignupPage />
              </RedirectIfAuthed>
            ),
          },
          { path: paths.passwordReset, element: <PasswordResetPage /> },
          {
            path: paths.passwordChange,
            element: (
              <RequireAuth>
                <PasswordChangePage />
              </RequireAuth>
            ),
          },
        ],
      },

      // ── 관람자 ──────────────────────────────────────────────────────
      {
        element: (
          <RequireAuth>
            <GalleryLayout />
          </RequireAuth>
        ),
        children: [
          { path: paths.gallery, element: <GalleryPage /> },
          { path: paths.galleryTheme, element: <ExhibitionThemePage /> },
          { path: routePatterns.galleryArtwork, element: <ArtworkPage /> },

          { path: paths.archive, element: <ArchivePage /> },
          // 아카이브는 갤러리와 **같은 컴포넌트를 재사용**한다(§5.2).
          { path: routePatterns.archiveDate, element: <GalleryPage /> },
          { path: routePatterns.archiveTheme, element: <ExhibitionThemePage /> },
          { path: routePatterns.archiveArtwork, element: <ArtworkPage /> },

          { path: paths.settings, element: <SettingsPage /> },
        ],
      },

      // ── 관리자 ──────────────────────────────────────────────────────
      {
        element: (
          <RequireCurator>
            <StudioLayout />
          </RequireCurator>
        ),
        children: [
          { path: paths.admin, element: <AdminDashboardPage /> },
          { path: routePatterns.adminExhibition, element: <ExhibitionEditorPage /> },
          { path: routePatterns.adminExhibitionTheme, element: <ThemeEditorPage /> },
          { path: routePatterns.adminExhibitionSlot, element: <ArtworkEditorPage /> },
          { path: paths.adminMembers, element: <MembersPage /> },
          { path: paths.adminSettings, element: <AdminSettingsPage /> },
          { path: paths.adminStats, element: <StatsPage /> },
          { path: routePatterns.adminMemberStats, element: <MemberStatsPage /> },
        ],
      },

      // 미리보기는 관람자 화면과 픽셀 단위로 같아야 하므로 Studio 레이아웃 밖에 둔다.
      {
        element: (
          <RequireCurator>
            <PlainLayout />
          </RequireCurator>
        ),
        children: [{ path: routePatterns.adminExhibitionPreview, element: <PreviewPage /> }],
      },

      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

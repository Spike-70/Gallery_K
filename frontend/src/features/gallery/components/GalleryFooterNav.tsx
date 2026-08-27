import { actions } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { TextLink } from '@/shared/ui'

/**
 * 갤러리 하단 링크 — UX 설계서 §3.6
 * `지난 전시` · `설정` · `첫 화면으로`. 되돌아갈 길이 항상 보인다(UX-3).
 */
export function GalleryFooterNav() {
  return (
    <nav className="flex flex-col items-center gap-2 py-8" aria-label="갤러리 이동">
      <TextLink to={paths.archive}>{actions.archive}</TextLink>
      <TextLink to={paths.settings}>{actions.settings}</TextLink>
      <TextLink to={paths.landing} tone="tertiary">
        {actions.backHome}
      </TextLink>
    </nav>
  )
}

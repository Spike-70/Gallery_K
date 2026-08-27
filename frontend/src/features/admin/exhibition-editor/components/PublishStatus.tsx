import { summarizeBlockers } from '@/entities/exhibition/model/admin'
import { screens, status, templates } from '@/shared/config/messages'

/**
 * 발행 조건 안내 — UX 설계서 §3.12
 *
 * **발행 버튼은 없다.** 조건이 채워지면 자동으로 걸린다(PRD §6.10).
 * 화면 하단에 남은 것을 항상 보여준다.
 */
export type PublishStatusProps = {
  isPublished: boolean
  blockers: string[]
}

export function PublishStatus({ isPublished, blockers }: PublishStatusProps) {
  if (isPublished && blockers.length === 0) {
    return <p className="text-body-sm text-tertiary">{screens.editor.publishedEditing}</p>
  }

  const summary = summarizeBlockers(blockers)
  const parts: string[] = []
  if (summary.missingArtworks > 0) parts.push(screens.editor.blockerArtwork(summary.missingArtworks))
  if (summary.missingTitle) parts.push(screens.editor.blockerTitle)
  if (summary.missingTheme) parts.push(screens.editor.blockerTheme)

  if (parts.length === 0) return <p className="text-body-sm text-tertiary">{status.published}</p>

  return <p className="text-body-sm text-secondary">{templates.publishPending(parts.join(', '))}</p>
}

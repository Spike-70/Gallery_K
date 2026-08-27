import type { SessionUser } from '@/entities/session/model/types'
import { screens } from '@/shared/config/messages'
import { Switch } from '@/shared/ui'

/**
 * 화면 섹션 — UX 설계서 §3.10
 * 큰 글씨는 즉시 반영된다. 토큰 스코프 교체 하나로 타이포와 그리드 열 수가 함께 바뀐다(S-1).
 */
export function FontScaleSection({
  user,
  onChange,
}: {
  user: SessionUser
  onChange: (patch: { fontScale: 'normal' | 'large' }) => void
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-label text-tertiary">{screens.settings.displaySection}</h2>
      <Switch
        label={screens.settings.fontScaleToggle}
        checked={user.fontScale === 'large'}
        onCheckedChange={(checked) => onChange({ fontScale: checked ? 'large' : 'normal' })}
      />
    </section>
  )
}

import { actions, screens } from '@/shared/config/messages'
import { Button, Icon } from '@/shared/ui'

/**
 * iOS 홈 화면 추가 안내 — PRD §6.14, UX 설계서 §3.3
 * iOS·비standalone에서는 **권한 요청보다 먼저** 이 안내를 보여준다.
 */
export function IosInstallGuide({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <h2 className="text-title-md text-primary">{screens.notifyPrompt.iosTitle}</h2>
      <p className="gk-prose text-center text-body-md text-secondary">{screens.notifyPrompt.iosBody}</p>

      {/* 도해 — 공유 버튼 → 홈 화면에 추가 */}
      <div className="flex items-center gap-3 rounded-md border border-border-default px-4 py-3">
        <Icon name="upload" size="md" className="text-secondary" />
        <Icon name="chevron-right" size="sm" className="text-tertiary" />
        <span className="flex items-center gap-2 text-body-sm text-secondary">
          <Icon name="plus" size="sm" />
          {screens.notifyPrompt.iosStepAdd}
        </span>
      </div>

      <Button size="lg" block onClick={onClose}>
        {actions.understood}
      </Button>
    </div>
  )
}

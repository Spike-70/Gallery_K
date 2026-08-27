import { type Member, needsIosGuide } from '@/entities/member/model/types'
import { landmarks, screens } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { formatPhone } from '@/shared/lib/phone'
import { Badge, Icon, Menu, type MenuItem } from '@/shared/ui'

/**
 * MemberRow — 디자인 시스템 문서 §8.3
 *
 * 이름 · 전화번호 · 가입일/마지막 입장 · 알림 상태 아이콘 · `⋯` 메뉴.
 * `iOS`이면서 알림을 못 받는 회원에는 배지를 단다 — **K가 전화로 도울 대상을
 * 찾을 수 있어야 한다**(PRD §6.14, U-6).
 */
export type MemberRowProps = {
  member: Member
  actions: MenuItem[]
}

/**
 * 알림 상태 3종 — UX §3.15.
 * `inactive`(구독은 있으나 실패 중)는 **벨 + `!`**로 표시한다.
 * 회색 벨과 보통 벨을 색만으로 구분하면 색을 못 보는 사람에게는 같은 그림이다(DS-5).
 */
const PUSH_ICON = {
  active: { name: 'bell', label: screens.members.pushActive, tone: 'text-secondary', warn: false },
  inactive: { name: 'bell', label: screens.members.pushInactive, tone: 'text-empty', warn: true },
  none: { name: 'bell-off', label: screens.members.pushNone, tone: 'text-tertiary', warn: false },
} as const

export function MemberRow({ member, actions }: MemberRowProps) {
  const push = PUSH_ICON[member.pushStatus]

  return (
    <li className="flex items-center gap-3 border-b border-border-default py-3">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="flex items-center gap-2">
          <span className="truncate text-title-sm text-primary">{member.name}</span>
          {member.isBlocked ? <Badge>{screens.members.filterBlocked}</Badge> : null}
          {needsIosGuide(member) ? <Badge tone="accent">iOS</Badge> : null}
        </span>
        <span className="tabular text-caption text-tertiary">{formatPhone(member.phone)}</span>
        <span className="text-caption text-tertiary">
          {screens.members.joinedAt} {member.createdAt.slice(0, 10)}
          {member.lastViewedOn ? ` · ${screens.members.lastViewed} ${member.lastViewedOn}` : ''}
        </span>
      </div>

      <span className={cn('relative inline-flex', push.tone)}>
        <Icon name={push.name} size="sm" label={push.label} />
        {push.warn ? (
          <span aria-hidden className="absolute -right-1 -top-1 text-caption font-bold leading-none">
            !
          </span>
        ) : null}
      </span>
      <Menu label={landmarks.memberActions(member.name)} items={actions} />
    </li>
  )
}

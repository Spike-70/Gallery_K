import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

import { landmarks } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { IconButton } from '@/shared/ui/IconButton'
import { TextLink } from '@/shared/ui/TextLink'

/**
 * BackLink — **모든 화면 하단의 필수 요소**(UX-3, 디자인 시스템 S-4)
 *
 * 시니어 사용자는 브라우저 뒤로가기도, 상단 아이콘도 쓰지 않는다(PRD §5.2).
 * 하단 텍스트 링크가 1급이며 상단 `←`는 보조 수단이다(UX §2.3).
 *
 * 이 컴포넌트는 두 곳(상단 포털·하단 링크)에 렌더되므로 단일 루트가 없다.
 * 그래서 `ref`를 받지 않는다 — 어디를 가리킬지 정할 수 없다(DS §8.4의 예외).
 *
 * **상단 `←`를 페이지가 따로 그리지 않는다.** 되돌아갈 대상을 아는 것은 페이지 하나뿐이고
 * (프런트 §8.1), 같은 대상을 두 곳에 적으면 언젠가 어긋난다. 그래서 이 컴포넌트가
 * 레이아웃이 열어 둔 자리(`TOP_BACK_SLOT_ID`)로 상단 버튼을 **포털로 보낸다.**
 */
export const TOP_BACK_SLOT_ID = 'gk-top-back'

export type BackLinkProps = {
  to: string
  label: string
  className?: string
}

/** 레이아웃이 상단 좌측에 한 번 놓는다. 비어 있으면 아무것도 차지하지 않는다. */
export function TopBackSlot({ className }: { className?: string }) {
  return <div id={TOP_BACK_SLOT_ID} className={cn('empty:hidden', className)} />
}

function TopBackButton({ to, label }: { to: string; label: string }) {
  const [slot, setSlot] = useState<HTMLElement | null>(null)

  // 자리는 레이아웃이 만든다. 커밋 이후에 찾아야 존재가 보장된다.
  useEffect(() => setSlot(document.getElementById(TOP_BACK_SLOT_ID)), [])

  if (!slot) return null
  return createPortal(<IconButton as="link" to={to} icon="back" label={label} />, slot)
}

export function BackLink({ to, label, className }: BackLinkProps) {
  return (
    <>
      <TopBackButton to={to} label={label} />
      <nav className={cn('flex justify-center py-8', className)} aria-label={landmarks.back}>
        <TextLink to={to}>{label}</TextLink>
      </nav>
    </>
  )
}

/** 되돌아갈 곳이 둘인 화면(지난 전시 상세)에서 쓴다. 상단 `←`는 **첫 번째** 대상을 따른다. */
export function BackLinkGroup({ links, className }: { links: BackLinkProps[]; className?: string }) {
  return (
    <>
      {links[0] ? <TopBackButton to={links[0].to} label={links[0].label} /> : null}
      <nav
        className={cn('flex flex-col items-center gap-2 py-8', className)}
        aria-label={landmarks.back}
      >
        {links.map((link) => (
          <TextLink key={link.to + link.label} to={link.to}>
            {link.label}
          </TextLink>
        ))}
      </nav>
    </>
  )
}

import type { SessionUser } from '@/entities/session/model/types'
import { screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { Divider, TextLink } from '@/shared/ui'

/** 계정 섹션 — 이름·전화번호는 읽기 전용이다(UX §3.10) */
export function AccountSection({ user }: { user: SessionUser }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-label text-tertiary">{screens.settings.accountSection}</h2>

      <dl className="m-0 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <dt className="text-body-md text-secondary">{screens.settings.nameLabel}</dt>
          <dd className="m-0 text-body-md text-primary">{user.name}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-body-md text-secondary">{screens.settings.phoneLabel}</dt>
          <dd className="tabular m-0 text-body-md text-primary">{user.phoneMasked}</dd>
        </div>
      </dl>

      {/*
        소셜로만 로그인하는 계정에는 바꿀 비밀번호가 없다(소셜 문서 §5.2).
        항목을 비활성으로 두지 않고 **감춘다** — 누를 수 없는 줄이 하나 남으면
        사용자는 자기가 무엇을 잘못했는지 찾는다.
      */}
      {user.hasPassword ? (
        <>
          <Divider className="my-2" />
          <TextLink to={paths.passwordChange}>{screens.settings.passwordChangeLink}</TextLink>
        </>
      ) : null}
    </section>
  )
}

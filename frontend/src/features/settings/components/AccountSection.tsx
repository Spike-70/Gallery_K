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

      <Divider className="my-2" />

      <TextLink to={paths.passwordChange}>{screens.settings.passwordChangeLink}</TextLink>
    </section>
  )
}

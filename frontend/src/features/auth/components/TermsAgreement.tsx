import { useState } from 'react'

import { TERMS_SECTIONS } from '@/features/auth/content/terms'
import { actions, screens } from '@/shared/config/messages'
import { BottomSheet, Checkbox, TextButton } from '@/shared/ui'

/**
 * 약관 동의 — UX 설계서 §3.3
 * 체크박스 1개 + `보기` 링크(바텀시트로 전문). 동의 항목을 쪼개지 않는다.
 */
export type TermsAgreementProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  error?: string
}

export function TermsAgreement({ checked, onChange, error }: TermsAgreementProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <Checkbox
          label={screens.signup.termsLabel}
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
        />
        <TextButton tone="tertiary" onClick={() => setOpen(true)}>
          {actions.viewTerms}
        </TextButton>
      </div>
      {error ? (
        <p role="alert" className="text-caption text-danger">
          {error}
        </p>
      ) : null}

      <BottomSheet open={open} title={screens.signup.termsTitle} onClose={() => setOpen(false)}>
        <div className="flex flex-col gap-6 pb-4">
          {TERMS_SECTIONS.map((section) => (
            <section key={section.heading} className="flex flex-col gap-2">
              <h3 className="text-title-sm text-primary">{section.heading}</h3>
              <p className="gk-prose text-body-md">{section.body}</p>
            </section>
          ))}
        </div>
      </BottomSheet>
    </div>
  )
}

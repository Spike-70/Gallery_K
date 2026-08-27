import { useState } from 'react'

import { SaveIndicator } from '@/features/admin/exhibition-editor/components/SaveIndicator'
import { readLocalDraft, useAutoSave } from '@/features/admin/exhibition-editor/hooks/useAutoSave'
import type { ExhibitionMetaForm } from '@/features/admin/exhibition-editor/model/editorSchemas'
import { LIMITS } from '@/shared/config/constants'
import { screens } from '@/shared/config/messages'
import { formatShortDate } from '@/shared/lib/date'
import type { IsoDate } from '@/shared/types/utility'
import { CharCounter, FieldGroup, TextArea, TextField } from '@/shared/ui'

/**
 * 전시 제목·테마 입력 폼 — UX 설계서 §3.13
 *
 * 초기값은 마운트 시 한 번만 읽는다. 호출부가 데이터를 받은 **뒤에** 이 컴포넌트를
 * 렌더하므로 동기화 effect가 필요 없다.
 */
export type ThemeEditorFormProps = {
  date: IsoDate
  initialValues: ExhibitionMetaForm
  save: (values: ExhibitionMetaForm) => Promise<void>
}

export function ThemeEditorForm({ date, initialValues, save }: ThemeEditorFormProps) {
  const scope = `${date}:meta`

  /**
   * 저장에 실패해 남아 있는 원고가 있으면 **그것으로 시작한다.**
   * 서버 값으로 덮으면 잃은 것이 무엇인지도 모른 채 사라진다(RISK-1, UX §3.12).
   */
  const [recovered] = useState(() => readLocalDraft<ExhibitionMetaForm>(scope))
  const [values, setValues] = useState<ExhibitionMetaForm>(recovered ?? initialValues)

  // 초과분은 서버가 거절한다. 저장을 멈추고 **어느 필드가 문제인지** 그 자리에 알린다(UX §3.13).
  const titleTooLong = values.title.length > LIMITS.exhibitionTitle
  const themeTooLong = values.theme.length > LIMITS.exhibitionTheme
  const tooLong = titleTooLong || themeTooLong

  const autoSave = useAutoSave<ExhibitionMetaForm>({
    scope,
    value: values,
    enabled: !tooLong,
    save,
  })

  return (
    <>
      <header className="flex items-center justify-between pb-6">
        <h1 className="tabular text-title-md text-primary">{formatShortDate(date)}</h1>
        <SaveIndicator state={autoSave.state} onRetry={() => void autoSave.retry()} />
      </header>

      <div className="flex flex-col gap-6">
        <FieldGroup
          id="exhibition-title"
          label={screens.editor.titleLabel}
          error={titleTooLong ? screens.editor.tooLong : undefined}
          trailing={<CharCounter current={values.title.length} max={LIMITS.exhibitionTitle} />}
        >
          <TextField
            id="exhibition-title"
            invalid={titleTooLong}
            value={values.title}
            onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))}
          />
        </FieldGroup>

        <FieldGroup
          id="exhibition-theme"
          label={screens.editor.themeLabel}
          hint={screens.editor.themeHint}
          error={themeTooLong ? screens.editor.tooLong : undefined}
          trailing={<CharCounter current={values.theme.length} max={LIMITS.exhibitionTheme} />}
        >
          <TextArea
            id="exhibition-theme"
            rows={8}
            autoGrow
            invalid={themeTooLong}
            value={values.theme}
            onChange={(event) => setValues((current) => ({ ...current, theme: event.target.value }))}
          />
        </FieldGroup>
      </div>
    </>
  )
}

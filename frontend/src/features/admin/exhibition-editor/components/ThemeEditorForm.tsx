import { useState } from 'react'

import { SaveIndicator } from '@/features/admin/exhibition-editor/components/SaveIndicator'
import { useAutoSave } from '@/features/admin/exhibition-editor/hooks/useAutoSave'
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
  const [values, setValues] = useState<ExhibitionMetaForm>(initialValues)
  const autoSave = useAutoSave<ExhibitionMetaForm>({
    scope: `${date}:meta`,
    value: values,
    enabled: true,
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
          trailing={<CharCounter current={values.title.length} max={LIMITS.exhibitionTitle} />}
        >
          <TextField
            id="exhibition-title"
            value={values.title}
            onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))}
          />
        </FieldGroup>

        <FieldGroup
          id="exhibition-theme"
          label={screens.editor.themeLabel}
          hint={screens.editor.themeHint}
          trailing={<CharCounter current={values.theme.length} max={LIMITS.exhibitionTheme} />}
        >
          <TextArea
            id="exhibition-theme"
            rows={8}
            value={values.theme}
            onChange={(event) => setValues((current) => ({ ...current, theme: event.target.value }))}
          />
        </FieldGroup>
      </div>
    </>
  )
}

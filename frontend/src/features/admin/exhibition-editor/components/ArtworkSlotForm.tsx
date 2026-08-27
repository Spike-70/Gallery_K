import { useState } from 'react'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { SaveIndicator } from '@/features/admin/exhibition-editor/components/SaveIndicator'
import { type ArtworkSlotForm as SlotFormValues, emptyToNull } from '@/features/admin/exhibition-editor/model/editorSchemas'
import { readLocalDraft, useAutoSave } from '@/features/admin/exhibition-editor/hooks/useAutoSave'
import { ARTWORK_DESCRIPTION_RECOMMENDED, LIMITS } from '@/shared/config/constants'
import { screens } from '@/shared/config/messages'
import type { IsoDate } from '@/shared/types/utility'
import { CharCounter, FieldGroup, TextArea, TextField } from '@/shared/ui'

/**
 * B-2-2. 그림 입력 폼 — UX 설계서 §3.14
 *
 * 모바일에서는 단독 화면으로, PC에서는 슬롯 그리드 우측 패널로 **같은 컴포넌트**가 쓰인다.
 * 12점 연속 입력의 효율이 운영 지속성(G3)을 좌우한다(U-10).
 *
 * 설명이 40자 미만이면 저장은 되지만 힌트가 바뀐다. **막지 않고 권한다.**
 *
 * 호출부는 `key={slot.position}`을 반드시 준다 — 슬롯이 바뀌면 폼이 새로 초기화되어야 한다.
 */
export type ArtworkSlotFormProps = {
  date: IsoDate
  slot: AdminSlot
  onSave: (values: {
    position: number
    title: string | null
    artist: string | null
    yearText: string | null
    description: string | null
    collection: string | null
    sourceUrl: string | null
  }) => Promise<void>
}

function toFormValues(slot: AdminSlot): SlotFormValues {
  return {
    title: slot.title ?? '',
    artist: slot.artist ?? '',
    yearText: slot.yearText ?? '',
    description: slot.description ?? '',
    collection: slot.collection ?? '',
    sourceUrl: slot.sourceUrl ?? '',
  }
}

export function ArtworkSlotForm({ date, slot, onSave }: ArtworkSlotFormProps) {
  const scope = `${date}:${slot.position}`

  // 다른 슬롯을 고르면 부모가 `key`를 바꿔 이 컴포넌트를 새로 만든다.
  // 동기화 effect 대신 마운트 한 번으로 초기화하는 편이 예측 가능하다.
  // 저장에 실패해 남아 있는 원고가 있으면 그것이 우선한다(RISK-1, UX §3.12).
  const [values, setValues] = useState<SlotFormValues>(
    () => readLocalDraft<SlotFormValues>(scope) ?? toFormValues(slot),
  )

  // 어느 한 칸이라도 넘치면 저장을 멈춘다 — 서버가 어차피 거절한다(UX §3.13 규칙 준용).
  const tooLong =
    values.title.length > LIMITS.artworkTitle ||
    values.artist.length > LIMITS.artworkArtist ||
    values.yearText.length > LIMITS.artworkYearText ||
    values.description.length > LIMITS.artworkDescription ||
    values.collection.length > LIMITS.artworkCollection

  const autoSave = useAutoSave<SlotFormValues>({
    scope,
    value: values,
    enabled: Boolean(slot.artworkId) && !tooLong,
    save: async (next) =>
      onSave({
        position: slot.position,
        title: emptyToNull(next.title),
        artist: emptyToNull(next.artist),
        yearText: emptyToNull(next.yearText),
        description: emptyToNull(next.description),
        collection: emptyToNull(next.collection),
        sourceUrl: emptyToNull(next.sourceUrl),
      }),
  })

  const set = <K extends keyof SlotFormValues>(key: K, value: SlotFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }))

  const descriptionHint =
    values.description.length > 0 && values.description.length < ARTWORK_DESCRIPTION_RECOMMENDED
      ? screens.editor.descriptionShortHint
      : screens.editor.descriptionHint

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h2 className="text-title-sm text-primary">
          {slot.position}. {screens.editor.imageLabel}
        </h2>
        <SaveIndicator state={autoSave.state} onRetry={() => void autoSave.retry()} />
      </div>

      <FieldGroup
        id={`slot-title-${slot.position}`}
        label={screens.editor.artworkTitleLabel}
        error={values.title.length > LIMITS.artworkTitle ? screens.editor.tooLong : undefined}
        trailing={<CharCounter current={values.title.length} max={LIMITS.artworkTitle} />}
      >
        <TextField
          id={`slot-title-${slot.position}`}
          value={values.title}
          onChange={(event) => set('title', event.target.value)}
        />
      </FieldGroup>

      <FieldGroup
        id={`slot-artist-${slot.position}`}
        label={screens.editor.artistLabel}
        error={values.artist.length > LIMITS.artworkArtist ? screens.editor.tooLong : undefined}
        trailing={<CharCounter current={values.artist.length} max={LIMITS.artworkArtist} />}
      >
        <TextField
          id={`slot-artist-${slot.position}`}
          value={values.artist}
          onChange={(event) => set('artist', event.target.value)}
        />
      </FieldGroup>

      <FieldGroup
        id={`slot-year-${slot.position}`}
        label={screens.editor.yearLabel}
        hint={screens.editor.yearHint}
        error={values.yearText.length > LIMITS.artworkYearText ? screens.editor.tooLong : undefined}
        trailing={<CharCounter current={values.yearText.length} max={LIMITS.artworkYearText} />}
      >
        <TextField
          id={`slot-year-${slot.position}`}
          value={values.yearText}
          onChange={(event) => set('yearText', event.target.value)}
        />
      </FieldGroup>

      <FieldGroup
        id={`slot-description-${slot.position}`}
        label={screens.editor.descriptionLabel}
        hint={descriptionHint}
        error={values.description.length > LIMITS.artworkDescription ? screens.editor.tooLong : undefined}
        trailing={<CharCounter current={values.description.length} max={LIMITS.artworkDescription} />}
      >
        <TextArea
          id={`slot-description-${slot.position}`}
          rows={6}
          autoGrow
          value={values.description}
          onChange={(event) => set('description', event.target.value)}
        />
      </FieldGroup>

      <FieldGroup
        id={`slot-collection-${slot.position}`}
        label={screens.editor.collectionLabel}
        hint={screens.editor.collectionHint}
        error={values.collection.length > LIMITS.artworkCollection ? screens.editor.tooLong : undefined}
        trailing={<CharCounter current={values.collection.length} max={LIMITS.artworkCollection} />}
      >
        <TextField
          id={`slot-collection-${slot.position}`}
          value={values.collection}
          onChange={(event) => set('collection', event.target.value)}
        />
      </FieldGroup>

      <FieldGroup
        id={`slot-source-${slot.position}`}
        label={screens.editor.sourceLabel}
        hint={screens.editor.sourceHint}
      >
        <TextField
          id={`slot-source-${slot.position}`}
          inputMode="url"
          value={values.sourceUrl}
          onChange={(event) => set('sourceUrl', event.target.value)}
        />
      </FieldGroup>
    </div>
  )
}

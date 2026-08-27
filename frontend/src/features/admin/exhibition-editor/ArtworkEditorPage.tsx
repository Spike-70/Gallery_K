import { useParams } from 'react-router-dom'

import {
  useAdminExhibitionQuery,
  useClearArtworkSlotMutation,
  useSaveArtworkSlotMutation,
} from '@/entities/exhibition/api/adminQueries'
import { ArtworkSlotForm } from '@/features/admin/exhibition-editor/components/ArtworkSlotForm'
import { UploadDropzone } from '@/features/admin/exhibition-editor/components/UploadDropzone'
import { useUploadQueue } from '@/features/admin/exhibition-editor/hooks/useUploadQueue'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import type { IsoDate } from '@/shared/types/utility'
import { useState } from 'react'
import { BackLink, Dialog, ErrorState, Skeleton, TextButton } from '@/shared/ui'

/**
 * B-2-2. 그림 입력 — UX 설계서 §3.14
 * 모바일 단독 화면. PC에서는 같은 폼이 B-2의 우측 패널로 들어간다.
 * 이미지 교체는 확인을 받는다.
 */
export function ArtworkEditorPage() {
  const { date, position } = useParams<{ date: IsoDate; position: string }>()
  const slotPosition = Number(position)
  const query = useAdminExhibitionQuery(date)
  const saveSlot = useSaveArtworkSlotMutation(date as IsoDate)
  const clearSlot = useClearArtworkSlotMutation(date as IsoDate)
  const upload = useUploadQueue(date as IsoDate, query.data?.slots)
  const [replaceOpen, setReplaceOpen] = useState(false)

  if (!date || Number.isNaN(slotPosition)) return null
  if (query.isPending) return <Skeleton className="h-6 w-full" lines={8} />
  if (query.isError || !query.data) {
    return <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
  }

  const slot = query.data.slots.find((candidate) => candidate.position === slotPosition)
  if (!slot) return null

  return (
    <>
      {slot.image ? (
        <div className="flex flex-col gap-3 pb-6">
          <img src={slot.image.displayUrl} alt="" className="max-h-image-preview w-full object-contain" />
          <div className="flex justify-between">
            <TextButton tone="accent" onClick={() => setReplaceOpen(true)}>
              {actions.replacePhoto}
            </TextButton>
            <TextButton tone="danger" onClick={() => clearSlot.mutate(slotPosition)}>
              {actions.clearSlot}
            </TextButton>
          </div>
        </div>
      ) : (
        <div className="pb-6">
          <UploadDropzone onFiles={(files) => void upload.upload(files)} disabled={upload.running} />
        </div>
      )}

      <ArtworkSlotForm
        key={slot.position}
        date={date}
        slot={slot}
        onSave={async (values) => {
          await saveSlot.mutateAsync(values)
        }}
      />

      <BackLink to={paths.adminExhibition(date)} label={actions.backPrev} />

      <Dialog
        open={replaceOpen}
        title={screens.editor.replaceConfirmTitle}
        description={screens.editor.replaceConfirmBody}
        confirmLabel={actions.replacePhoto}
        onConfirm={() => {
          setReplaceOpen(false)
          clearSlot.mutate(slotPosition)
        }}
        onClose={() => setReplaceOpen(false)}
      />
    </>
  )
}

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  useAdminExhibitionQuery,
  useReorderArtworksMutation,
  useSaveArtworkSlotMutation,
} from '@/entities/exhibition/api/adminQueries'
import { ArtworkSlotForm } from '@/features/admin/exhibition-editor/components/ArtworkSlotForm'
import { PublishStatus } from '@/features/admin/exhibition-editor/components/PublishStatus'
import { SlotGrid } from '@/features/admin/exhibition-editor/components/SlotGrid'
import { UploadDropzone } from '@/features/admin/exhibition-editor/components/UploadDropzone'
import { useSlotPolling } from '@/features/admin/exhibition-editor/hooks/useSlotPolling'
import { useUploadQueue } from '@/features/admin/exhibition-editor/hooks/useUploadQueue'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screens, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useIsDesktop } from '@/shared/hooks/useMediaQuery'
import { formatShortDate } from '@/shared/lib/date'
import type { IsoDate } from '@/shared/types/utility'
import { BackLink, ErrorState, LinkButton, Skeleton, StatusChip, toast } from '@/shared/ui'

/**
 * B-2. 작품·큐레이션 업로드 — UX 설계서 §3.12
 *
 * 큐레이터가 가장 오래 머무는 화면. PC와 모바일을 동등하게 지원한다(PRD §6.9).
 * **≥1024px에서는 좌측 슬롯 그리드 + 우측 입력 폼**으로 화면 이동 없이 12점을 연속 입력한다(U-10).
 */
export function ExhibitionEditorPage() {
  const { date } = useParams<{ date: IsoDate }>()
  const isDesktop = useIsDesktop()
  const [selectedPosition, setSelectedPosition] = useState(1)

  const query = useAdminExhibitionQuery(date)
  const polling = useSlotPolling(query.data?.slots)

  const upload = useUploadQueue(date as IsoDate, query.data?.slots)
  const saveSlot = useSaveArtworkSlotMutation(date as IsoDate)
  const reorder = useReorderArtworksMutation(date as IsoDate)

  // 발행되는 순간을 한 번만 알린다(UX §3.12).
  const publishedNow = saveSlot.data?.exhibition.publishedNow
  useEffect(() => {
    if (publishedNow) toast.info(status.published)
  }, [publishedNow])

  useEffect(() => {
    if (polling.timedOut) toast.error(status.processingDelayed)
  }, [polling.timedOut])

  if (!date) return null

  if (query.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
  }

  const exhibition = query.data
  const selectedSlot = exhibition.slots.find((slot) => slot.position === selectedPosition) ?? exhibition.slots[0]

  const editor = (
    <div className="flex flex-col gap-6">
      <header className="flex items-center justify-between">
        <h1 className="tabular text-title-md text-primary">{formatShortDate(exhibition.date)}</h1>
        <StatusChip status={exhibition.isPublished ? 'published' : 'empty'} />
      </header>

      {/* 전시 테마 카드 — 탭하면 B-2-1 */}
      <Link
        to={paths.adminExhibitionTheme(exhibition.date)}
        className="flex flex-col gap-1 rounded-md border border-border-default p-4"
      >
        <span className="text-label text-tertiary">{screens.editor.themeCardTitle}</span>
        <span className="text-body-md text-primary">
          {exhibition.title ?? screens.editor.themeCardEmpty}
        </span>
      </Link>

      <SlotGrid
        date={exhibition.date}
        slots={exhibition.slots}
        progress={upload.progress}
        onReorder={(order) => reorder.mutate(order)}
      />

      <UploadDropzone onFiles={(files) => void upload.upload(files)} disabled={upload.running} />

      <div className="flex flex-col gap-3">
        <PublishStatus isPublished={exhibition.isPublished} blockers={exhibition.publishBlockers} />
        <LinkButton to={paths.adminExhibitionPreview(exhibition.date)} variant="secondary" size="md" block>
          {actions.preview}
        </LinkButton>
      </div>
    </div>
  )

  return (
    <>
      {isDesktop ? (
        <div className="grid grid-cols-[minmax(0,420px)_1fr] gap-8">
          <div>{editor}</div>
          <aside className="border-l border-border-default pl-8">
            {selectedSlot?.artworkId ? (
              <ArtworkSlotForm
                key={selectedSlot.position}
                date={exhibition.date}
                slot={selectedSlot}
                onSave={async (values) => {
                  await saveSlot.mutateAsync(values)
                }}
              />
            ) : (
              <p className="text-body-sm text-tertiary">{screens.editor.slotEmpty}</p>
            )}
            <div className="flex flex-wrap gap-2 pt-6">
              {exhibition.slots.map((slot) => (
                <button
                  key={slot.position}
                  type="button"
                  onClick={() => setSelectedPosition(slot.position)}
                  aria-current={slot.position === selectedPosition}
                  className="tabular min-h-touch min-w-touch rounded-md border border-border-default text-body-sm text-secondary aria-[current=true]:border-accent aria-[current=true]:text-accent"
                >
                  {slot.position}
                </button>
              ))}
            </div>
          </aside>
        </div>
      ) : (
        editor
      )}

      <BackLink to={paths.admin} label={actions.backAdmin} />
    </>
  )
}

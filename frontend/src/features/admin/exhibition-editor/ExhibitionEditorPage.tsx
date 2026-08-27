import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  useAdminExhibitionQuery,
  useReorderArtworksMutation,
  useSaveArtworkSlotMutation,
  useSetExhibitionHiddenMutation,
} from '@/entities/exhibition/api/adminQueries'
import { ArtworkSlotForm } from '@/features/admin/exhibition-editor/components/ArtworkSlotForm'
import { PublishStatus } from '@/features/admin/exhibition-editor/components/PublishStatus'
import { SaveIndicator, type SaveState } from '@/features/admin/exhibition-editor/components/SaveIndicator'
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
import { BackLink, Banner, Dialog, ErrorState, LinkButton, Skeleton, StatusChip, TextButton, toast } from '@/shared/ui'

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

  // 폴링은 60초에서 멈춘다. 멈춘 뒤에는 화면이 지연을 알리고 재시도 수단을 준다(API §9.9).
  const [pollingStopped, setPollingStopped] = useState(false)
  const query = useAdminExhibitionQuery(date, { polling: !pollingStopped })
  const polling = useSlotPolling(query.data?.slots)

  const upload = useUploadQueue(date as IsoDate, query.data?.slots)
  const saveSlot = useSaveArtworkSlotMutation(date as IsoDate)
  const reorder = useReorderArtworksMutation(date as IsoDate)
  const reorderState: SaveState = reorder.isPending
    ? 'saving'
    : reorder.isError
      ? 'failed'
      : reorder.isSuccess
        ? 'saved'
        : 'idle'
  const setHidden = useSetExhibitionHiddenMutation()
  const [hideConfirmOpen, setHideConfirmOpen] = useState(false)

  // 발행되는 순간을 한 번만 알린다(UX §3.12).
  const publishedNow = saveSlot.data?.exhibition.publishedNow
  useEffect(() => {
    if (publishedNow) toast.info(status.published)
  }, [publishedNow])

  useEffect(() => {
    if (polling.timedOut) setPollingStopped(true)
  }, [polling.timedOut])

  if (!date) return null

  if (query.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-block w-full" />
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

      {/* 숨김은 되돌릴 수 있지만 관람자에게는 즉시 사라진다. 상태를 숨기지 않고 먼저 알린다. */}
      {exhibition.isHidden ? (
        <Banner tone="info" message={screens.editor.hiddenBanner} />
      ) : null}

      {/* 전시 테마 카드 — 탭하면 B-2-1 */}
      <Link
        to={paths.adminExhibitionTheme(exhibition.date)}
        className="flex flex-col gap-1 rounded-md border border-border-default p-4"
      >
        <span className="text-label text-tertiary">{screens.editor.themeCardTitle}</span>
        <span className="text-body-md text-primary">
          {exhibition.title ?? screens.editor.themeCardEmpty}
        </span>
        <span className="tabular text-caption text-tertiary">
          {screens.editor.themeCardCounter(exhibition.title?.length ?? 0, exhibition.theme?.length ?? 0)}
        </span>
      </Link>

      {/* 처리가 60초를 넘기면 폴링을 멈추고 **그 자리에서** 다시 확인할 수단을 준다(§10 체감 성능). */}
      {pollingStopped ? (
        <Banner
          tone="info"
          message={status.processingDelayed}
          action={
            <TextButton
              tone="accent"
              onClick={() => {
                setPollingStopped(false)
                void query.refetch()
              }}
            >
              {actions.retry}
            </TextButton>
          }
        />
      ) : null}

      <div className="flex items-center justify-between">
        <span className="text-label text-tertiary">{screens.editor.slotsSection}</span>
        {/* 순서 변경도 저장이다. 저장됐는지를 같은 표시로 알린다(UX §3.12). */}
        <SaveIndicator state={reorderState} onRetry={() => reorder.reset()} />
      </div>

      <SlotGrid
        date={exhibition.date}
        slots={exhibition.slots}
        progress={upload.progress}
        onReorder={(order) => reorder.mutate(order)}
        selectable={isDesktop}
        selectedPosition={selectedPosition}
        onSelect={setSelectedPosition}
        onReupload={() => void query.refetch()}
      />

      <UploadDropzone onFiles={(files) => void upload.upload(files)} disabled={upload.running} />

      <div className="flex flex-col gap-3">
        <LinkButton to={paths.adminExhibitionPreview(exhibition.date)} variant="secondary" size="md" block>
          {actions.preview}
        </LinkButton>
        <PublishStatus isPublished={exhibition.isPublished} blockers={exhibition.publishBlockers} />
      </div>

      {/*
        전시 숨김 — PRD §6.9. 저작권 문제를 뒤늦게 발견했을 때의 **유일한 철회 수단**이다.
        B 화면의 3열은 스캔 속도를 위해 고정이므로(UX §3.11) 조작은 이 화면에 둔다.
        발행된 전시에만 의미가 있다.
      */}
      {exhibition.isPublished || exhibition.isHidden ? (
        <div className="flex justify-center pt-2">
          <TextButton
            tone={exhibition.isHidden ? 'accent' : 'danger'}
            onClick={() => setHideConfirmOpen(true)}
          >
            {exhibition.isHidden ? actions.unhideExhibition : actions.hideExhibition}
          </TextButton>
        </div>
      ) : null}
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
          </aside>
        </div>
      ) : (
        editor
      )}

      <BackLink to={paths.admin} label={actions.backAdmin} />

      <Dialog
        open={hideConfirmOpen}
        title={exhibition.isHidden ? screens.editor.unhideConfirmTitle : screens.editor.hideConfirmTitle}
        description={exhibition.isHidden ? screens.editor.unhideConfirmBody : screens.editor.hideConfirmBody}
        confirmLabel={exhibition.isHidden ? actions.unhideExhibition : actions.hideExhibition}
        destructive={!exhibition.isHidden}
        loading={setHidden.isPending}
        onConfirm={() => {
          setHidden.mutate({ date: exhibition.date, hidden: !exhibition.isHidden })
          setHideConfirmOpen(false)
        }}
        onClose={() => setHideConfirmOpen(false)}
      />
    </>
  )
}

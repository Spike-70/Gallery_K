import { useParams } from 'react-router-dom'

import {
  useAdminExhibitionQuery,
  useSaveExhibitionMetaMutation,
} from '@/entities/exhibition/api/adminQueries'
import { ThemeEditorForm } from '@/features/admin/exhibition-editor/components/ThemeEditorForm'
import { emptyToNull } from '@/features/admin/exhibition-editor/model/editorSchemas'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import type { IsoDate } from '@/shared/types/utility'
import { BackLink, ErrorState, Skeleton, toast } from '@/shared/ui'

/**
 * B-2-1. 전시 테마 입력 — UX 설계서 §3.13
 *
 * 페이지는 **데이터 훅 → 상태 분기 → 표현 컴포넌트 조합**만 한다(프런트 §8.1).
 * 입력 상태는 폼 컴포넌트가 소유하며, 데이터가 도착한 뒤에 마운트되므로
 * 초기값 동기화 문제가 생기지 않는다.
 */
export function ThemeEditorPage() {
  const { date } = useParams<{ date: IsoDate }>()
  const query = useAdminExhibitionQuery(date)
  const mutation = useSaveExhibitionMetaMutation(date as IsoDate)

  if (!date) return null
  if (query.isPending) return <Skeleton className="h-6 w-full" lines={6} />
  if (query.isError || !query.data) {
    return <ErrorState message={resolveErrorMessage(query.error)} onRetry={() => void query.refetch()} />
  }

  const exhibition = query.data

  return (
    <>
      <ThemeEditorForm
        date={date}
        initialValues={{ title: exhibition.title ?? '', theme: exhibition.theme ?? '' }}
        save={async (values) => {
          const result = await mutation.mutateAsync({
            title: emptyToNull(values.title),
            theme: emptyToNull(values.theme),
            version: exhibition.version,
          })
          // 발행 조건이 **처음** 충족된 순간만 알린다(API 문서 §9.4).
          if (result.publishedNow) toast.info(status.published)
        }}
      />

      <BackLink to={paths.adminExhibition(date)} label={actions.backPrev} />
    </>
  )
}

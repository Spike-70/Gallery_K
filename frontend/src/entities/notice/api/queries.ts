import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import * as noticeApi from '@/entities/notice/api/noticeApi'
import { CACHE_POLICY } from '@/shared/api/queryClient'

export const noticeKeys = {
  all: ['admin', 'notices'] as const,
  list: (includePast: boolean) => ['admin', 'notices', { includePast }] as const,
}

export function useNoticesQuery(includePast = false) {
  return useQuery({
    queryKey: noticeKeys.list(includePast),
    queryFn: () => noticeApi.fetchNotices(includePast),
    ...CACHE_POLICY.admin,
  })
}

function useInvalidateNotices() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: noticeKeys.all })
}

export function useCreateNoticeMutation() {
  const invalidate = useInvalidateNotices()
  return useMutation({ mutationFn: noticeApi.createNotice, onSuccess: () => void invalidate() })
}

export function useDeleteNoticeMutation() {
  const invalidate = useInvalidateNotices()
  return useMutation({ mutationFn: noticeApi.deleteNotice, onSuccess: () => void invalidate() })
}

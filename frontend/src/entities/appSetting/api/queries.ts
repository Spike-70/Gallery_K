import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import * as settingApi from '@/entities/appSetting/api/settingApi'
import { CACHE_POLICY } from '@/shared/api/queryClient'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { toast } from '@/shared/ui'

export const settingKeys = {
  all: ['admin', 'settings'] as const,
}

export function useSettingsQuery() {
  return useQuery({
    queryKey: settingKeys.all,
    queryFn: settingApi.fetchSettings,
    ...CACHE_POLICY.admin,
  })
}

export function useUpdateSettingsMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: settingApi.updateSettings,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin'] })
    },
    onError: (error) => toast.error(resolveErrorMessage(error)),
  })
}

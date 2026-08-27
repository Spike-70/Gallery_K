import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKeys } from '@/entities/session/api/keys'
import { type SettingsPatch, updateSettings } from '@/entities/session/api/meApi'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { toast } from '@/shared/ui'

/**
 * C-4 설정 변경 — 프런트엔드 아키텍처 문서 §6.4
 *
 * 알림 on/off와 큰 글씨는 **낙관적으로 반영**한다. 실패하면 롤백하고 토스트를 띄운다.
 * 관람자 화면에 성공 토스트는 없다 — 정상 동작에 시스템이 끼어들지 않는다(UX §6).
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient()
  const user = useSessionStore((state) => state.user)
  const updateUser = useSessionStore((state) => state.updateUser)

  return useMutation({
    mutationFn: (patch: SettingsPatch) => updateSettings(patch),

    onMutate: (patch) => {
      const previous = user
      if (previous) {
        updateUser({
          ...previous,
          notifyEnabled: patch.notifyEnabled ?? previous.notifyEnabled,
          notifyAt: patch.notifyAt ?? previous.notifyAt,
          fontScale: patch.fontScale ?? previous.fontScale,
        })
      }
      return { previous }
    },

    onError: (error, _patch, context) => {
      if (context?.previous) updateUser(context.previous)
      toast.error(resolveErrorMessage(error))
    },

    onSuccess: (nextUser) => {
      updateUser(nextUser)
      void queryClient.invalidateQueries({ queryKey: sessionKeys.me() })
    },
  })
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { withdraw } from '@/entities/session/api/meApi'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { toast } from '@/shared/ui'

/**
 * 탈퇴 — UX 설계서 §3.10
 * 확인은 **한 번만** 받는다. 문구 입력 같은 추가 관문을 두지 않는다.
 * 완료하면 A 첫 화면으로 보내고 토스트 하나를 남긴다.
 */
export function useWithdraw() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setAnonymous = useSessionStore((state) => state.setAnonymous)

  return useMutation({
    mutationFn: withdraw,
    onSuccess: () => {
      setAnonymous()
      queryClient.clear()
      toast.info(screens.settings.withdrawDone)
      navigate(paths.landing, { replace: true })
    },
    onError: (error) => toast.error(resolveErrorMessage(error)),
  })
}

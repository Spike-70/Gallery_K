import { useEffect, useState } from 'react'

import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { IMAGE_POLL_TIMEOUT_MS } from '@/shared/config/constants'

/**
 * 이미지 처리 폴링 — API 명세서 §9.9
 *
 * 폴링 주기 자체는 쿼리(`useAdminExhibitionQuery`)가 갖는다. 이 훅은 **60초를 넘겼는지**만
 * 판정해 "처리가 지연되고 있습니다" 안내를 띄울 시점을 알려 준다. 무한 대기를 두지 않는다.
 */
export function useSlotPolling(slots: AdminSlot[] | undefined) {
  const pending =
    slots?.some((slot) => slot.imageStatus === 'processing' || slot.imageStatus === 'uploading') ?? false
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!pending) return
    const timer = window.setTimeout(() => setTimedOut(true), IMAGE_POLL_TIMEOUT_MS)
    return () => {
      window.clearTimeout(timer)
      setTimedOut(false)
    }
  }, [pending])

  return { pending, timedOut }
}

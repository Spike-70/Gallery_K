import { QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode, useEffect, useState } from 'react'

import { artworkKeys } from '@/entities/artwork/api/keys'
import { registerImageRecovery } from '@/entities/artwork/model/imageRecovery'
import { exhibitionKeys } from '@/entities/exhibition/api/keys'
import { createQueryClient } from '@/shared/api/queryClient'

/** TanStack Query 프로바이더. 클라이언트는 마운트당 1개만 만든다. */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)

  /**
   * 이미지가 연속으로 실패하면 URL 만료를 의심하고 그림을 담은 쿼리를 무효화한다(F-12).
   * 다시 받은 응답에는 새 presigned URL이 들어 있다.
   */
  useEffect(() => {
    registerImageRecovery(async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: exhibitionKeys.all }),
        queryClient.invalidateQueries({ queryKey: artworkKeys.all }),
      ])
    })
  }, [queryClient])

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

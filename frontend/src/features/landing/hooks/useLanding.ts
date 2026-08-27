import { useQuery } from '@tanstack/react-query'

import { fetchLanding } from '@/features/landing/api/landingApi'
import { CACHE_POLICY } from '@/shared/api/queryClient'

export const landingKeys = {
  all: ['landing'] as const,
}

/** A 화면 데이터. 실패해도 화면은 그대로 뜬다(FA-7). */
export function useLanding() {
  return useQuery({
    queryKey: landingKeys.all,
    queryFn: fetchLanding,
    ...CACHE_POLICY.landing,
    refetchOnWindowFocus: true,
    retry: 1,
  })
}

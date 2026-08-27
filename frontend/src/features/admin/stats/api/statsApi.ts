// [API]
// import { endpoints } from '@/shared/api/endpoints'
// import { httpClient } from '@/shared/api/httpClient'
// import type { RawMemberStatsDay, RawStatsDay } from '@/shared/api/types'
import type { IsoDate, Uuid } from '@/shared/types/utility'

// [MOCK]
import * as adminMock from '@/mocks/handlers/adminHandlers'

/**
 * 관람 현황 API *(v1.1)* — API 명세서 §9.19
 * 경로와 스키마는 MVP 시점에 확정되어 있다. 나중에 붙일 때 계약 협의를 다시 하지 않는다.
 */
export type StatsDay = {
  date: IsoDate
  exhibitionTitle: string | null
  isCarriedOver: boolean
  entrantCount: number
  artworkViewCount: number
}

export type MemberStatsDay = {
  date: IsoDate
  exhibitionTitle: string | null
  entered: boolean
  viewedArtworkCount: number
  totalArtworkCount: number
}

export async function fetchDailyStats(days = 7): Promise<StatsDay[]> {
  // [API]
  // const raw = await httpClient.get<{ days: RawStatsDay[] }>(endpoints.admin.statsDaily(), {
  //   query: { from: ..., to: ... },
  // })

  // [MOCK]
  const raw = await adminMock.getDailyStats(days)

  return raw.days.map((day) => ({
    date: day.date,
    exhibitionTitle: day.exhibition_title,
    isCarriedOver: day.is_carried_over,
    entrantCount: day.entrant_count,
    artworkViewCount: day.artwork_view_count,
  }))
}

export async function searchMembers(query: string): Promise<
  { id: Uuid; name: string; phoneMasked: string; lastViewedOn: IsoDate | null }[]
> {
  // [API]
  // const raw = await httpClient.get<{ members: {...}[] }>(endpoints.admin.statsMembers(), {
  //   query: { query },
  // })

  // [MOCK]
  const raw = await adminMock.searchMembersForStats(query)

  return raw.members.map((member) => ({
    id: member.id,
    name: member.name,
    phoneMasked: member.phone_masked,
    lastViewedOn: member.last_viewed_on,
  }))
}

export async function fetchMemberStats(
  memberId: Uuid,
  days = 30,
): Promise<{ member: { id: Uuid; name: string; phoneMasked: string }; days: MemberStatsDay[] }> {
  // [API]
  // const raw = await httpClient.get<{...}>(endpoints.admin.statsMember(memberId), { query: { days } })

  // [MOCK]
  const raw = await adminMock.getMemberStats(memberId, days)

  return {
    member: { id: raw.member.id, name: raw.member.name, phoneMasked: raw.member.phone_masked },
    days: raw.days.map((day) => ({
      date: day.date,
      exhibitionTitle: day.exhibition_title,
      entered: day.entered,
      viewedArtworkCount: day.viewed_artwork_count,
      totalArtworkCount: day.total_artwork_count,
    })),
  }
}

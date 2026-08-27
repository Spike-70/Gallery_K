import { endpoints } from '@/shared/api/endpoints'
import { httpClient } from '@/shared/api/httpClient'
import type { RawMemberStatsDay, RawStatsDay } from '@/shared/api/types'
import type { IsoDate, Uuid } from '@/shared/types/utility'

/**
 * 관람 현황 API *(v1.1)* — API 명세서 §9.19
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

export type MemberStatsResult = {
  member: { id: Uuid; name: string; phoneMasked: string }
  days: MemberStatsDay[]
}

/**
 * `GET /admin/stats/daily` — B-1의 최근 7일.
 *
 * 범위(`from`·`to`)를 보내지 않는다. **오늘이 언제인지는 서버가 정한다**(PRD §6.1) —
 * 단말 시계로 역산한 범위를 보내면 자정 전후에 화면과 서버의 "오늘"이 갈라진다.
 * 생략하면 서버가 KST 오늘을 끝으로 하는 기본 창(7일)을 돌려준다.
 */
export async function fetchDailyStats(): Promise<StatsDay[]> {
  const raw = await httpClient.get<{ days: RawStatsDay[] }>(endpoints.admin.statsDaily())

  return raw.days.map((day) => ({
    date: day.date,
    exhibitionTitle: day.exhibition_title,
    isCarriedOver: day.is_carried_over,
    entrantCount: day.entrant_count,
    artworkViewCount: day.artwork_view_count,
  }))
}

/** `GET /admin/stats/members` — 이름 또는 번호 완전일치 후보. 번호는 마스킹되어 온다. */
export async function searchMembers(
  query: string,
): Promise<{ id: Uuid; name: string; phoneMasked: string; lastViewedOn: IsoDate | null }[]> {
  const raw = await httpClient.get<{
    members: { id: Uuid; name: string; phone_masked: string; last_viewed_on: IsoDate | null }[]
  }>(endpoints.admin.statsMembers(), { query: { query } })

  return raw.members.map((member) => ({
    id: member.id,
    name: member.name,
    phoneMasked: member.phone_masked,
    lastViewedOn: member.last_viewed_on,
  }))
}

/** `GET /admin/stats/members/{id}` — B-1-1. `days`는 서버가 상한(90)으로 자른다. */
export async function fetchMemberStats(memberId: Uuid, days: number): Promise<MemberStatsResult> {
  const raw = await httpClient.get<{
    member: { id: Uuid; name: string; phone_masked: string }
    days: RawMemberStatsDay[]
  }>(endpoints.admin.statsMember(memberId), { query: { days } })

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

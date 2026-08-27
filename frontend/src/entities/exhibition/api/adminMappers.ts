import { toImageSet } from '@/entities/artwork/api/mappers'
import type {
  AdminExhibition,
  AdminExhibitionDay,
  AdminSlot,
  AdminSummary,
} from '@/entities/exhibition/model/admin'
import type {
  RawAdminExhibitionDay,
  RawAdminExhibitionDetail,
  RawAdminArtworkSlot,
  RawAdminSummary,
} from '@/shared/api/types'

export function toAdminSlot(raw: RawAdminArtworkSlot): AdminSlot {
  return {
    position: raw.position,
    artworkId: raw.artwork_id,
    title: raw.title,
    artist: raw.artist,
    yearText: raw.year_text,
    description: raw.description,
    collection: raw.collection,
    sourceUrl: raw.source_url,
    imageStatus: raw.image_status,
    image: raw.image ? toImageSet(raw.image) : null,
    imageErrorCode: raw.image_error_code,
    isComplete: raw.is_complete,
    version: raw.version,
  }
}

export function toAdminExhibition(raw: RawAdminExhibitionDetail): AdminExhibition {
  return {
    date: raw.exhibition_date,
    title: raw.title,
    theme: raw.theme,
    isPublished: raw.is_published,
    publishedAt: raw.published_at,
    isHidden: raw.is_hidden,
    editMode: raw.edit_mode,
    canPublish: raw.can_publish,
    publishBlockers: raw.publish_blockers,
    slots: raw.slots.map(toAdminSlot),
    version: raw.version,
    draftUpdatedAt: raw.draft_updated_at,
    carryDraftSource: raw.carry_draft_source
      ? { fromDate: raw.carry_draft_source.from_date, artworkCount: raw.carry_draft_source.artwork_count }
      : null,
  }
}

export function toAdminDay(raw: RawAdminExhibitionDay): AdminExhibitionDay {
  return {
    date: raw.date,
    status: raw.status,
    title: raw.title,
    carriedFromDate: raw.carried_from_date,
    carriedFromTitle: raw.carried_from_title,
    hasDraft: raw.has_draft,
    draftProgress: {
      artworkCount: raw.draft_progress.artwork_count,
      completeArtworkCount: raw.draft_progress.complete_artwork_count,
      hasTitle: raw.draft_progress.has_title,
      hasTheme: raw.draft_progress.has_theme,
    },
    isHidden: raw.is_hidden,
    isEditable: raw.is_editable,
    editMode: raw.edit_mode,
    isToday: raw.is_today,
    updatedAt: raw.updated_at,
  }
}

export function toAdminSummary(raw: RawAdminSummary): AdminSummary {
  return {
    todayEntrantCount: raw.today_entrant_count,
    weeklyActiveRatio: raw.weekly_active_ratio,
    weeklyActiveCount: raw.weekly_active_count,
    totalMemberCount: raw.total_member_count,
    carriedOverDays: raw.carried_over_days,
    pendingDraftCount: raw.pending_draft_count,
    leadTimeDays: raw.lead_time_days,
  }
}

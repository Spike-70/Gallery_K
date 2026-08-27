import { z } from 'zod'

import { LIMITS } from '@/shared/config/constants'
import { validation } from '@/shared/config/messages'

/**
 * 편집 폼 스키마 — API 명세서 §9.4·§9.5
 *
 * 글자 수 초과는 **입력을 막지 않고** 저장 시 차단한다(PRD §6.10). 따라서 스키마는
 * 저장 직전 검증에만 쓰이며, 입력 중에는 `CharCounter`가 숫자 색으로만 알린다.
 */
export const exhibitionMetaSchema = z.object({
  title: z.string().max(LIMITS.exhibitionTitle, validation.tooLong(LIMITS.exhibitionTitle)),
  theme: z.string().max(LIMITS.exhibitionTheme, validation.tooLong(LIMITS.exhibitionTheme)),
})
export type ExhibitionMetaForm = z.infer<typeof exhibitionMetaSchema>

export const artworkSlotSchema = z.object({
  title: z.string().max(LIMITS.artworkTitle, validation.tooLong(LIMITS.artworkTitle)),
  artist: z.string().max(LIMITS.artworkArtist, validation.tooLong(LIMITS.artworkArtist)),
  yearText: z.string().max(LIMITS.artworkYearText, validation.tooLong(LIMITS.artworkYearText)),
  description: z.string().max(LIMITS.artworkDescription, validation.tooLong(LIMITS.artworkDescription)),
  collection: z.string().max(LIMITS.artworkCollection, validation.tooLong(LIMITS.artworkCollection)),
  sourceUrl: z
    .string()
    .max(LIMITS.artworkSourceUrl, validation.tooLong(LIMITS.artworkSourceUrl))
    .refine((value) => value === '' || value.startsWith('https://'), validation.urlFormat),
})
export type ArtworkSlotForm = z.infer<typeof artworkSlotSchema>

/** 서버는 빈 문자열이 아니라 `null`을 기대한다(API 문서 §2.1). */
export function emptyToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length === 0 ? null : trimmed
}

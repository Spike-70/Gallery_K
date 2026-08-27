import { env } from '@/shared/config/env'

/**
 * 미술관 정문 이미지 — PRD §6.1
 *
 * 공개 경로의 **고정 이미지 한 장**이다(`media/public/entrance.jpg`). 작품 이미지는
 * 서명 URL 뒤에 있으며 이 자리에 절대 오지 않는다(PRD §8.4).
 * 폭 100% · 종횡비 4:3 고정. **탭해도 반응하지 않는다. 장식이다**(UX §3.1).
 */
export function EntranceImage() {
  return (
    <img
      src={env.entranceImageUrl}
      alt=""
      aria-hidden
      width={960}
      height={720}
      loading="eager"
      decoding="async"
      className="aspect-[4/3] w-full object-cover"
    />
  )
}

// [MOCK] 데모용 정문 이미지. 실제 서비스에서는 `media/public/entrance.jpg`를 쓴다.
import { entranceImageUrl } from '@/mocks/lib/imageFactory'

/**
 * 미술관 정문 이미지 — PRD §6.1
 * 폭 100% · 종횡비 4:3 고정. **탭해도 반응하지 않는다. 장식이다**(UX §3.1).
 */
export function EntranceImage() {
  return (
    <img
      src={entranceImageUrl}
      alt=""
      aria-hidden
      width={960}
      height={720}
      className="aspect-[4/3] w-full object-cover"
    />
  )
}

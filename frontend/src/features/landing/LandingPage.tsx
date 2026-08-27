import { useNavigate } from 'react-router-dom'

import { paths } from '@/shared/config/paths'
import { useSessionStore } from '@/entities/session/model/sessionStore'
import { DateLine } from '@/entities/exhibition/ui/DateLine'
import { NoticeBanner } from '@/entities/exhibition/ui/NoticeBanner'
import { EntranceImage } from '@/features/landing/components/EntranceImage'
import { useLanding } from '@/features/landing/hooks/useLanding'
import { actions, brand, screens } from '@/shared/config/messages'
import { Button, Skeleton, TextLink } from '@/shared/ui'

/**
 * A. 첫 화면 — UX 설계서 §3.1
 *
 * **데이터 없이도 완전한 레이아웃을 렌더한다**(F-4, PRD §6.1).
 * 어떤 API가 실패해도 정문 이미지와 입장 버튼은 보인다. 오류 메시지를 띄우지 않는다.
 *
 * 모든 진입은 이 화면을 거친다(알림 클릭 포함). 휴관 공지처럼 첫 화면에만 있는 것을
 * 놓치지 않게 하기 위함이다(UX §4.2).
 */
export function LandingPage() {
  const { data } = useLanding()
  const navigate = useNavigate()
  const sessionStatus = useSessionStore((state) => state.status)

  // 세션 표시를 화면에 두지 않는다. **누르는 순간 판정한다**(UX §3.1).
  const handleEnter = () => {
    navigate(sessionStatus === 'authenticated' ? paths.gallery : paths.login)
  }

  return (
    <div className="gk-container-gallery flex min-h-screen flex-col py-6">
      {/* 큐레이터에게만 렌더한다. UI 은닉은 편의일 뿐 보안이 아니다(PRD §8.4). */}
      {data?.isCurator ? (
        <div className="flex justify-end">
          <TextLink to={paths.admin} tone="tertiary">
            {brand.curatorLink}
          </TextLink>
        </div>
      ) : null}

      <header className="flex flex-col items-center gap-2 pt-8">
        {data ? (
          <DateLine label={data.todayLabel} />
        ) : (
          <Skeleton className="h-4 w-32" />
        )}
        <h1 className="text-display text-primary">{brand.logo}</h1>

        {/* 전시 제목은 비회원에게도 노출한다 — 무엇을 얻는지 먼저 보여준다(PRD §5.1). */}
        <div className="min-h-[2.5em] pt-2">
          {data ? (
            <p className="text-center text-title-lg text-primary">
              {data.hasExhibition ? data.exhibitionTitle : screens.landing.firstExhibitionPending}
            </p>
          ) : (
            <Skeleton className="h-7 w-52" />
          )}
        </div>
      </header>

      {data?.notice ? <NoticeBanner notice={data.notice} archiveTo={paths.archive} className="mt-4" /> : null}

      <div className="mt-8">
        <EntranceImage />
      </div>

      <div className="mt-8 flex flex-col items-center gap-2">
        <Button size="lg" block onClick={handleEnter}>
          {actions.enterGallery}
        </Button>
        {/* 가입 잠금이어도 링크를 숨기지 않는다. 숨기면 초대받은 사람이 당황한다(UX §3.1). */}
        <TextLink to={paths.signup} tone="tertiary">
          {actions.signup}
        </TextLink>
      </div>
    </div>
  )
}

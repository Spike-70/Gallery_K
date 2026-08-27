import { useSocialProvidersQuery } from '@/entities/session/api/queries'
import { screens } from '@/shared/config/messages'
import { socialStartUrl } from '@/shared/config/paths'
import { buttonVariants } from '@/shared/ui'
import { cn } from '@/shared/lib/cn'

/**
 * 소셜 로그인 버튼 — UX 설계서 §3.2, 소셜 문서 §11
 *
 * A-1 로그인과 D 설정이 **같은 버튼을 쓴다.** 두 기능이 공유하는 도메인 표현이라
 * `entities`에 둔다 — `features` 사이의 직접 참조를 만들지 않기 위해서다(FA-1).
 *
 * **`<a href>`다. `onClick`으로 주소를 바꾸지 않는다.** 자바스크립트가 로드되기 전에
 * 눌러도 동작해야 하며, 반응 없는 버튼을 대상 사용자는 두 번 세 번 누른다(P2).
 *
 * 팝업을 열지 않는 이유는 §2에 있다 — iOS Safari에서 차단되기 쉽고, 차단되면
 * 아무 일도 일어나지 않아 원인을 알 수 없다. 화면이 실제로 넘어가야 보인다.
 *
 * 켜진 제공자가 없으면 **구분선까지 통째로 그리지 않는다.**
 */
export type SocialButtonsProps = {
  /** 로그인 후 돌아갈 앱 내부 경로 */
  next: string
  /** 문구를 `연결하기`로 바꾼다(D 설정 화면) */
  variant?: 'start' | 'link'
  /** 이미 연결된 제공자는 숨긴다 */
  hidden?: readonly string[]
}

export function SocialButtons({ next, variant = 'start', hidden = [] }: SocialButtonsProps) {
  const { data } = useSocialProvidersQuery()
  const providers = (data ?? []).filter((provider) => !hidden.includes(provider.provider))
  if (providers.length === 0) return null

  return (
    <div className="flex flex-col gap-3">
      {variant === 'start' ? (
        <div className="flex items-center gap-4 py-2">
          <span className="h-px flex-1 bg-border-default" />
          <span className="text-caption text-tertiary">{screens.social.divider}</span>
          <span className="h-px flex-1 bg-border-default" />
        </div>
      ) : null}

      {providers.map((provider) => (
        <a
          key={provider.provider}
          href={socialStartUrl(provider.startUrl, next)}
          className={cn(buttonVariants({ variant: 'secondary', size: 'lg', block: true }))}
        >
          {variant === 'start'
            ? screens.social.startWith(provider.label)
            : screens.social.linkWith(provider.label)}
        </a>
      ))}
    </div>
  )
}

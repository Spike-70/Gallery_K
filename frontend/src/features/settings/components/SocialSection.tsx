import { useSocialIdentitiesQuery, useUnlinkSocialMutation } from '@/entities/session/api/queries'
import { SocialButtons } from '@/entities/session/ui/SocialButtons'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { screens } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { formatShortDate } from '@/shared/lib/date'
import { ErrorState, Skeleton, TextButton, toast } from '@/shared/ui'

/**
 * 연결된 로그인 — UX 설계서 §3.10, 소셜 문서 §5.3
 *
 * **마지막 로그인 수단은 해제할 수 없다.** 비밀번호가 없는 계정이 유일한 연결을
 * 끊으면 들어올 길이 0이 된다. 판정은 서버가 `can_unlink`로 내려 주며, 화면은
 * 그 값을 믿는다 — 프런트가 다시 계산하면 규칙이 두 곳에 생긴다.
 */
export function SocialSection() {
  const query = useSocialIdentitiesQuery()
  const unlink = useUnlinkSocialMutation()

  if (query.isPending) return <Skeleton className="h-12 w-full" lines={2} />
  if (query.isError) {
    return (
      <ErrorState
        size="inline"
        message={resolveErrorMessage(query.error)}
        onRetry={() => void query.refetch()}
      />
    )
  }

  const { identities, canUnlink } = query.data

  const handleUnlink = (id: string) => {
    unlink.mutate(id, {
      onSuccess: () => toast.info(screens.social.unlinked),
      onError: (error) => toast.error(resolveErrorMessage(error)),
    })
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-label text-tertiary">{screens.settings.socialSection}</h2>

      {identities.length > 0 ? (
        <ul className="list-none p-0">
          {identities.map((identity) => (
            <li
              key={identity.id}
              className="flex min-h-touch items-center justify-between gap-4 border-b border-border-default py-2"
            >
              <div className="flex flex-col">
                <span className="text-body-md text-primary">
                  {screens.social.linkedWith(identity.label)}
                </span>
                <span className="tabular text-caption text-tertiary">
                  {formatShortDate(identity.linkedAt.slice(0, 10))}
                </span>
              </div>
              <TextButton
                tone="danger"
                disabled={!canUnlink || unlink.isPending}
                onClick={() => handleUnlink(identity.id)}
              >
                {screens.social.unlink}
              </TextButton>
            </li>
          ))}
        </ul>
      ) : null}

      {!canUnlink && identities.length > 0 ? (
        <p className="text-caption text-tertiary">{screens.social.lastIdentityHint}</p>
      ) : null}

      {/* 돌아올 곳은 설정 화면이다 — 연결하러 왔다가 갤러리로 튕기지 않게 한다. */}
      <SocialButtons
        next={paths.settings}
        variant="link"
        hidden={identities.map((identity) => identity.provider)}
      />
    </section>
  )
}

import { useSessionStore } from '@/entities/session/model/sessionStore'
import { AccountSection } from '@/features/settings/components/AccountSection'
import { FontScaleSection } from '@/features/settings/components/FontScaleSection'
import { NotifySection } from '@/features/settings/components/NotifySection'
import { SocialSection } from '@/features/settings/components/SocialSection'
import { WithdrawSection } from '@/features/settings/components/WithdrawSection'
import { useUpdateSettings } from '@/features/settings/hooks/useUpdateSettings'
import { actions, screenTitles } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { BackLink, Divider, Skeleton } from '@/shared/ui'

/** C-4. 설정 — UX 설계서 §3.10 */
export function SettingsPage() {
  const user = useSessionStore((state) => state.user)
  const mutation = useUpdateSettings()

  if (!user) {
    return <Skeleton className="h-4 w-full" lines={6} />
  }

  return (
    <>
      <h1 className="pb-6 text-center text-title-md text-primary">{screenTitles.settings}</h1>

      <div className="flex flex-col gap-8">
        <NotifySection user={user} onChange={(patch) => mutation.mutate(patch)} />
        <Divider />
        <FontScaleSection user={user} onChange={(patch) => mutation.mutate(patch)} />
        <Divider />
        <SocialSection />
        <Divider />
        <AccountSection user={user} />
        <WithdrawSection />
      </div>

      <BackLink to={paths.gallery} label={actions.backGallery} />
    </>
  )
}

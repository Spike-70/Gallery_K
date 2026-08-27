import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { SETTING_KEYS } from '@/entities/appSetting/model/types'
import { useUpdateSettingsMutation } from '@/entities/appSetting/api/queries'
import { useMembersQuery, useSetMemberBlockedMutation } from '@/entities/member/api/queries'
import type { Member } from '@/entities/member/model/types'
import { MemberRow } from '@/entities/member/ui/MemberRow'
import { CreateMemberDialog } from '@/features/admin/members/components/CreateMemberDialog'
import { ResetPasswordSheet } from '@/features/admin/members/components/ResetPasswordSheet'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { actions, screenTitles, screens, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue'
import {
  BackLink,
  Button,
  Dialog,
  EmptyState,
  ErrorState,
  FilterChip,
  Skeleton,
  Switch,
  TextField,
} from '@/shared/ui'

type FilterKey = 'all' | 'blocked' | 'notifyOff'

/**
 * B-3. 회원 관리 — UX 설계서 §3.15
 *
 * **목록의 필터·검색어는 URL에 둔다**(프런트 §6.1). 특정 필터 상태를 새 탭으로 열거나
 * 새로고침해도 유지되어야 한다.
 *
 * 차단은 되돌리기 어려운 조작이므로 낙관적 반영을 하지 않고 확인을 받는다(UX-6).
 * 다이얼로그는 차단의 **한계를 그대로 알린다** — 즉시 끊긴다고 오해하면 운영 판단이 틀어진다.
 */
export function MembersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filter = (searchParams.get('filter') ?? 'all') as FilterKey
  const query = searchParams.get('query') ?? ''

  const [searchInput, setSearchInput] = useState(query)
  const debouncedSearch = useDebouncedValue(searchInput, 300)

  const listQuery = useMembersQuery({
    query: debouncedSearch || undefined,
    status: filter === 'blocked' ? 'blocked' : 'all',
    notify: filter === 'notifyOff' ? 'off' : 'all',
  })

  const blockMutation = useSetMemberBlockedMutation()
  const settingsMutation = useUpdateSettingsMutation()

  const [blockTarget, setBlockTarget] = useState<Member | null>(null)
  const [resetTarget, setResetTarget] = useState<Member | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const setFilter = (next: FilterKey) => {
    const params = new URLSearchParams(searchParams)
    if (next === 'all') params.delete('filter')
    else params.set('filter', next)
    setSearchParams(params, { replace: true })
  }

  const commitSearch = (value: string) => {
    setSearchInput(value)
    const params = new URLSearchParams(searchParams)
    if (value) params.set('query', value)
    else params.delete('query')
    setSearchParams(params, { replace: true })
  }

  const signupOpen = listQuery.data?.signupOpen ?? false

  return (
    <>
      <h1 className="pb-6 text-title-md text-primary">{screenTitles.adminMembers}</h1>

      <Switch
        label={screens.members.signupOpenLabel}
        description={signupOpen ? screens.members.signupOpenOn : screens.members.signupOpenOff}
        checked={signupOpen}
        onCheckedChange={(checked) => settingsMutation.mutate({ [SETTING_KEYS.signupOpen]: checked })}
      />

      <div className="flex flex-col gap-3 py-4">
        <TextField
          aria-label={screens.members.searchPlaceholder}
          placeholder={screens.members.searchPlaceholder}
          value={searchInput}
          onChange={(event) => commitSearch(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <FilterChip label={screens.members.filterAll} selected={filter === 'all'} onSelect={() => setFilter('all')} />
          <FilterChip
            label={screens.members.filterBlocked}
            selected={filter === 'blocked'}
            onSelect={() => setFilter('blocked')}
          />
          <FilterChip
            label={screens.members.filterNotifyOff}
            selected={filter === 'notifyOff'}
            onSelect={() => setFilter('notifyOff')}
          />
        </div>
      </div>

      {listQuery.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-20 w-full" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <ErrorState message={resolveErrorMessage(listQuery.error)} onRetry={() => void listQuery.refetch()} />
      ) : listQuery.data.items.length === 0 ? (
        <EmptyState
          message={status.memberEmpty}
          icon="plus"
          action={<Button size="md" onClick={() => setCreateOpen(true)}>{actions.createAccount}</Button>}
        />
      ) : (
        <ul className="list-none p-0">
          {listQuery.data.items.map((member) => (
            <MemberRow
              key={member.id}
              member={member}
              actions={[
                { label: actions.resetPassword, onSelect: () => setResetTarget(member) },
                member.isBlocked
                  ? {
                      label: actions.unblock,
                      onSelect: () => blockMutation.mutate({ id: member.id, blocked: false }),
                    }
                  : { label: actions.block, onSelect: () => setBlockTarget(member), destructive: true },
              ]}
            />
          ))}
        </ul>
      )}

      <div className="py-6">
        <Button size="md" block variant="secondary" onClick={() => setCreateOpen(true)}>
          {actions.createAccount}
        </Button>
      </div>

      <BackLink to={paths.admin} label={actions.backAdmin} />

      <Dialog
        open={Boolean(blockTarget)}
        title={blockTarget ? screens.members.blockTitle(blockTarget.name) : ''}
        description={screens.members.blockBody}
        confirmLabel={actions.block}
        destructive
        loading={blockMutation.isPending}
        onConfirm={() => {
          if (blockTarget) blockMutation.mutate({ id: blockTarget.id, blocked: true })
          setBlockTarget(null)
        }}
        onClose={() => setBlockTarget(null)}
      />

      <ResetPasswordSheet member={resetTarget} onClose={() => setResetTarget(null)} />

      <CreateMemberDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  )
}

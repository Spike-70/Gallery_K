import { useState } from 'react'

import { useSettingsQuery, useUpdateSettingsMutation } from '@/entities/appSetting/api/queries'
import { useCreateNoticeMutation, useDeleteNoticeMutation, useNoticesQuery } from '@/entities/notice/api/queries'
import { ERROR_CODES, isApiError } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { LIMITS } from '@/shared/config/constants'
import { actions, screenTitles, screens, status } from '@/shared/config/messages'
import { paths } from '@/shared/config/paths'
import {
  BackLink,
  Button,
  CharCounter,
  DateField,
  Divider,
  EmptyState,
  ErrorState,
  FieldGroup,
  Skeleton,
  Switch,
  TextArea,
  TextButton,
  TextField,
} from '@/shared/ui'

/**
 * 관리자 설정 · 휴관 공지 — UX 설계서 §3.16
 *
 * 공지는 저장 전 **미리보기**를 보여준다. 기간이 겹치면 서버가 `NOTICE_PERIOD_OVERLAP`으로
 * 막고, 화면은 그 문구를 그대로 띄운다.
 *
 * 운영 설정에는 위험한 값을 두지 않으며, 각 항목에 한 줄 설명을 붙인다.
 */
export function AdminSettingsPage() {
  const settingsQuery = useSettingsQuery()
  const noticesQuery = useNoticesQuery()
  const updateSettings = useUpdateSettingsMutation()
  const createNotice = useCreateNoticeMutation()
  const deleteNotice = useDeleteNoticeMutation()

  const [startsOn, setStartsOn] = useState('')
  const [endsOn, setEndsOn] = useState('')
  const [body, setBody] = useState('')
  const [noticeError, setNoticeError] = useState<string | null>(null)
  /** 기간이 겹친 상대 공지 — 그 공지로 데려가지 않으면 무엇과 겹쳤는지 알 수 없다(UX §3.16). */
  const [conflictNoticeId, setConflictNoticeId] = useState<string | null>(null)

  /** 서버가 상대 공지 id를 주지 않으면 화면이 가진 목록에서 겹치는 기간을 찾는다. */
  const findOverlapping = (): string | null =>
    noticesQuery.data?.find((notice) => notice.startsOn <= endsOn && startsOn <= notice.endsOn)?.id ??
    null

  const submitNotice = async () => {
    setNoticeError(null)
    setConflictNoticeId(null)
    try {
      await createNotice.mutateAsync({ startsOn, endsOn, body })
      setStartsOn('')
      setEndsOn('')
      setBody('')
    } catch (error) {
      setNoticeError(resolveErrorMessage(error))
      if (isApiError(error) && error.code === ERROR_CODES.noticePeriodOverlap) {
        const conflict = error.details?.conflict_notice_id
        setConflictNoticeId(typeof conflict === 'string' ? conflict : findOverlapping())
      }
    }
  }

  return (
    <>
      <h1 className="pb-6 text-title-md text-primary">{screenTitles.adminSettings}</h1>

      <section className="flex flex-col gap-4">
        <h2 className="text-title-sm text-primary">{screens.adminSettings.noticeSection}</h2>

        {noticesQuery.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : noticesQuery.isError ? (
          <ErrorState
            size="inline"
            message={resolveErrorMessage(noticesQuery.error)}
            onRetry={() => void noticesQuery.refetch()}
          />
        ) : noticesQuery.data.length === 0 ? (
          <EmptyState message={status.noticeEmpty} icon="calendar" />
        ) : (
          <ul className="list-none p-0">
            {noticesQuery.data.map((notice) => (
              <li
                key={notice.id}
                id={`notice-${notice.id}`}
                className="flex items-start justify-between gap-4 border-b border-border-default py-3"
              >
                <div className="flex flex-col gap-1">
                  <span className="tabular text-caption text-tertiary">
                    {notice.startsOn} ~ {notice.endsOn}
                  </span>
                  <span className="text-body-md text-primary">{notice.body}</span>
                </div>
                <TextButton tone="danger" onClick={() => deleteNotice.mutate(notice.id)}>
                  {actions.cancel}
                </TextButton>
              </li>
            ))}
          </ul>
        )}

        <div className="flex flex-col gap-4 rounded-md border border-border-default p-4">
          {noticeError ? (
            <div role="alert" className="flex flex-col gap-1">
              <p className="text-caption text-danger">{noticeError}</p>
              {conflictNoticeId ? (
                <TextButton
                  tone="accent"
                  onClick={() => {
                    document
                      .getElementById(`notice-${conflictNoticeId}`)
                      ?.scrollIntoView({ block: 'center' })
                  }}
                >
                  {screens.adminSettings.noticeConflictLink}
                </TextButton>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <FieldGroup id="notice-start" label={screens.adminSettings.noticeStart}>
              <DateField id="notice-start" value={startsOn} onChange={(event) => setStartsOn(event.target.value)} />
            </FieldGroup>
            <FieldGroup id="notice-end" label={screens.adminSettings.noticeEnd}>
              <DateField id="notice-end" value={endsOn} onChange={(event) => setEndsOn(event.target.value)} />
            </FieldGroup>
          </div>

          <FieldGroup
            id="notice-body"
            label={screens.adminSettings.noticeBody}
            trailing={<CharCounter current={body.length} max={LIMITS.noticeBody} />}
          >
            <TextArea
              id="notice-body"
              rows={3}
              placeholder={screens.adminSettings.noticeBodyPlaceholder}
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
          </FieldGroup>

          {/* 저장 전 미리보기 — 관람자에게 보일 모습 그대로 */}
          {body ? (
            <div className="rounded-md border border-border-default p-4 text-center">
              <p className="text-caption text-tertiary">{screens.adminSettings.noticePreview}</p>
              <p className="mt-2 text-body-sm text-secondary">{body}</p>
            </div>
          ) : null}

          <Button
            size="md"
            block
            loading={createNotice.isPending}
            disabled={!startsOn || !endsOn || !body}
            onClick={() => void submitNotice()}
          >
            {actions.addNotice}
          </Button>
        </div>
      </section>

      <Divider className="my-8" />

      <section className="flex flex-col gap-4">
        <h2 className="text-title-sm text-primary">{screens.adminSettings.operationSection}</h2>

        {settingsQuery.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : settingsQuery.isError ? (
          <ErrorState
            size="inline"
            message={resolveErrorMessage(settingsQuery.error)}
            onRetry={() => void settingsQuery.refetch()}
          />
        ) : (
          <ul className="list-none p-0">
            {settingsQuery.data.map((setting) => (
              <li key={setting.key} className="flex flex-col gap-2 border-b border-border-default py-4">
                {setting.valueType === 'boolean' ? (
                  <Switch
                    label={screens.settingLabels[setting.key] ?? setting.key}
                    description={setting.description}
                    checked={Boolean(setting.value)}
                    disabled={!setting.isMutable}
                    onCheckedChange={(checked) => updateSettings.mutate({ [setting.key]: checked })}
                  />
                ) : (
                  <FieldGroup
                    id={`setting-${setting.key}`}
                    label={screens.settingLabels[setting.key] ?? setting.key}
                    hint={setting.description}
                  >
                    <TextField
                      id={`setting-${setting.key}`}
                      defaultValue={String(setting.value)}
                      disabled={!setting.isMutable}
                      onBlur={(event) =>
                        updateSettings.mutate({
                          [setting.key]:
                            setting.valueType === 'number' ? Number(event.target.value) : event.target.value,
                        })
                      }
                    />
                  </FieldGroup>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <BackLink to={paths.admin} label={actions.backAdmin} />
    </>
  )
}

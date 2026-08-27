import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { adminExhibitionKeys } from '@/entities/exhibition/api/adminKeys'
import * as adminApi from '@/entities/exhibition/api/adminExhibitionApi'
import type { AdminSlot } from '@/entities/exhibition/model/admin'
import { ERROR_CODES } from '@/shared/api/ApiError'
import { resolveErrorMessage } from '@/shared/api/errorMessages'
import { ApiError } from '@/shared/api/ApiError'
import { UPLOAD_ALLOWED_MIME, UPLOAD_CONCURRENCY, UPLOAD_MAX_BYTES } from '@/shared/config/constants'
import { fallbackMessageFor } from '@/shared/api/errorMessages'
import { screens } from '@/shared/config/messages'
import { logger } from '@/shared/lib/logger'
import type { IsoDate } from '@/shared/types/utility'
import { toast } from '@/shared/ui'

/**
 * 다중 업로드 — UX 설계서 §3.12, API 명세서 §11.2
 *
 * 1. 빈 슬롯에 **번호 순서대로** 배정한다. 파일이 더 많으면 초과분을 알리고 배정하지 않는다.
 * 2. presigned POST 자격을 배치 발급받는다.
 * 3. **동시 3개**씩 S3로 직접 POST 한다(20MB는 API Gateway를 통과할 수 없다).
 * 4. 각 파일 완료 즉시 `image/complete`를 부르면 서버가 **동기로** 변환을 끝내고 응답한다.
 * 5. 전부 끝나면 편집 쿼리를 무효화한다. 폴링하지 않는다(API 문서 §9.9).
 * 6. 처리 완료 순서와 무관하게 **슬롯 위치는 고정**된다.
 *
 * `httpClient` 밖에서 `fetch`를 쓰는 예외 모듈이다(프런트 §7.1).
 */
export type UploadProgress = Record<number, number>

export function useUploadQueue(date: IsoDate, slots: AdminSlot[] | undefined) {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState<UploadProgress>({})
  const [running, setRunning] = useState(false)

  const validate = (file: File): string | null => {
    if (!UPLOAD_ALLOWED_MIME.includes(file.type as (typeof UPLOAD_ALLOWED_MIME)[number])) {
      return fallbackMessageFor(ERROR_CODES.uploadMimeNotAllowed)
    }
    if (file.size > UPLOAD_MAX_BYTES) {
      return fallbackMessageFor(ERROR_CODES.uploadFileTooLarge)
    }
    return null
  }

  const upload = useCallback(
    async (files: File[]) => {
      const emptyPositions = (slots ?? [])
        .filter((slot) => slot.imageStatus === 'empty')
        .map((slot) => slot.position)
        .sort((a, b) => a - b)

      const assigned = files.slice(0, emptyPositions.length)
      const overflow = files.length - assigned.length
      if (overflow > 0) toast.info(screens.editor.uploadOverflow(overflow))
      if (assigned.length === 0) return

      for (const file of assigned) {
        const problem = validate(file)
        if (problem) {
          toast.error(problem)
          return
        }
      }

      setRunning(true)
      try {
        const tickets = await adminApi.requestUploadUrls(
          date,
          assigned.map((file, index) => ({
            position: emptyPositions[index],
            filename: file.name,
            contentType: file.type,
            sizeBytes: file.size,
            // [MOCK] 데모에서 실제 파일을 화면에 그대로 보여주기 위한 값이다.
            objectUrl: URL.createObjectURL(file),
          })),
        )

        // 동시 3개 제한 — 창을 밀며 진행한다.
        let cursor = 0
        const workers = Array.from({ length: Math.min(UPLOAD_CONCURRENCY, tickets.length) }, async () => {
          while (cursor < tickets.length) {
            const index = cursor
            cursor += 1
            const ticket = tickets[index]
            const file = assigned[index]
            try {
              await postToStorage(ticket.uploadUrl, ticket.fields, file, (value) =>
                setProgress((current) => ({ ...current, [ticket.position]: value })),
              )
              await adminApi.completeImageUpload(ticket.artworkId, ticket.objectKey)
            } catch (error) {
              logger.warn('upload failed', ticket.position, error)
              toast.error(resolveErrorMessage(error))
            } finally {
              setProgress((current) => {
                const next = { ...current }
                delete next[ticket.position]
                return next
              })
            }
          }
        })

        await Promise.all(workers)
        // 완료 통지 응답으로 처리가 끝나 있다. 최신 슬롯 상태를 한 번만 다시 받는다.
        await queryClient.invalidateQueries({ queryKey: adminExhibitionKeys.exhibition(date) })
        toast.info(screens.editor.uploadDone(assigned.length))
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : resolveErrorMessage(error))
      } finally {
        setRunning(false)
      }
    },
    [date, slots, queryClient],
  )

  return { upload, progress, running }
}

/**
 * S3 직접 업로드(presigned POST). 서명 필드를 **먼저** 담고 파일을 마지막에 붙인다 —
 * S3는 `file` 이후의 필드를 무시한다.
 *
 * 진행률이 필요하므로 `XMLHttpRequest`를 쓴다 — `fetch`는 업로드 진행률을 노출하지 않는다.
 * 데모에서는 `mock://` 스킴이라 실제 전송 없이 진행률만 흉내 낸다.
 */
function postToStorage(
  url: string,
  fields: Record<string, string>,
  file: File,
  onProgress: (value: number) => void,
): Promise<void> {
  // [MOCK] 실제 배포에서는 이 분기가 존재하지 않는다.
  if (url.startsWith('mock://')) {
    return new Promise((resolve) => {
      let value = 0
      const timer = window.setInterval(() => {
        value = Math.min(100, value + 20)
        onProgress(value)
        if (value >= 100) {
          window.clearInterval(timer)
          resolve()
        }
      }, 120)
    })
  }

  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) form.append(key, value)
  form.append('file', file)

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', url)
    request.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    })
    request.addEventListener('load', () =>
      request.status >= 200 && request.status < 300
        ? resolve()
        : reject(new Error(`upload failed: ${request.status}`)),
    )
    request.addEventListener('error', () => reject(new Error('upload failed')))
    request.send(form)
  })
}

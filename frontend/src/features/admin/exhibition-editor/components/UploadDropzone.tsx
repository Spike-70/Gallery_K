import { useRef, useState } from 'react'

import { UPLOAD_ALLOWED_MIME } from '@/shared/config/constants'
import { actions, screens } from '@/shared/config/messages'
import { cn } from '@/shared/lib/cn'
import { Button, Icon } from '@/shared/ui'

/**
 * 다중 파일 선택 — UX 설계서 §3.12
 * 드래그&드롭(PC) + 파일 선택(모바일). 두 경로 모두 같은 핸들러로 들어간다.
 */
export type UploadDropzoneProps = {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export function UploadDropzone({ onFiles, disabled }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        onFiles(Array.from(event.dataTransfer.files))
      }}
      className={cn(
        'flex flex-col items-center gap-3 rounded-md border border-dashed p-6 text-center',
        dragging ? 'border-accent bg-accent-subtle' : 'border-border-strong',
      )}
    >
      <Icon name="upload" size="lg" className="text-tertiary" />
      <p className="text-caption text-tertiary">{screens.editor.imageHint}</p>
      <Button size="md" disabled={disabled} onClick={() => inputRef.current?.click()}>
        {actions.uploadMany}
      </Button>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={UPLOAD_ALLOWED_MIME.join(',')}
        className="gk-sr-only"
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []))
          event.target.value = ''
        }}
      />
    </div>
  )
}

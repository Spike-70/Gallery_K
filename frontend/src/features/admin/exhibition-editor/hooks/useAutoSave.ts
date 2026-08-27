import { useCallback, useEffect, useRef, useState } from 'react'

import type { SaveState } from '@/features/admin/exhibition-editor/components/SaveIndicator'
import { AUTOSAVE_DEBOUNCE_MS } from '@/shared/config/constants'
import { STORAGE_KEYS, localStore } from '@/shared/lib/storage'

/**
 * 자동 임시저장 — UX 설계서 §3.12, PRD §6.10
 *
 * 입력 후 1.2초 디바운스 + **화면 이탈 시 즉시 저장**.
 * 저장에 실패하면 입력 내용을 로컬에 보존하고 재시도 버튼을 제공한다 —
 * **12점 × 설명은 하루치 노동이고, 그것을 잃는 것이 RISK-1이다.**
 */
export type UseAutoSaveOptions<T> = {
  /** 로컬 보존 키를 구분하는 식별자(날짜·슬롯 등) */
  scope: string
  value: T
  /** 저장할 값이 있는가. 초기 로딩 중에는 false를 준다. */
  enabled: boolean
  save: (value: T) => Promise<void>
}

/**
 * 저장에 실패해 로컬에 남아 있는 원고를 읽는다.
 *
 * **폼이 마운트되기 전에 읽어야 한다** — 초기값으로 써야 하기 때문이다. 그래서 훅이 아니다.
 * 이것이 없으면 원고는 저장만 되고 **다시 열었을 때 사라진 것처럼 보인다**(RISK-1).
 */
export function readLocalDraft<T>(scope: string): T | null {
  return localStore.getJson<T | null>(`${STORAGE_KEYS.editorDraft}:${scope}`, null)
}

export function useAutoSave<T>({ scope, value, enabled, save }: UseAutoSaveOptions<T>) {
  const [state, setState] = useState<SaveState>('idle')
  const latest = useRef(value)
  const savedSnapshot = useRef<string | null>(null)
  const timer = useRef<number | null>(null)

  // 렌더 중 ref를 건드리지 않는다. 최신 값 반영은 커밋 이후에 한다.
  useEffect(() => {
    latest.current = value
  }, [value])

  const flush = useCallback(async () => {
    if (!enabled) return
    const snapshot = JSON.stringify(latest.current)
    if (snapshot === savedSnapshot.current) return

    setState('saving')
    try {
      await save(latest.current)
      savedSnapshot.current = snapshot
      localStore.remove(`${STORAGE_KEYS.editorDraft}:${scope}`)
      setState('saved')
    } catch {
      // 서버 저장에 실패해도 원고는 남긴다.
      localStore.setJson(`${STORAGE_KEYS.editorDraft}:${scope}`, latest.current)
      setState('failed')
    }
  }, [enabled, save, scope])

  // 디바운스 저장
  useEffect(() => {
    if (!enabled) return
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => void flush(), AUTOSAVE_DEBOUNCE_MS)
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [value, enabled, flush])

  // 화면 이탈 시 즉시 저장
  useEffect(() => {
    return () => {
      void flush()
    }
  }, [flush])

  /** 저장 실패로 로컬에 남아 있는 원고 */
  const recoverLocalDraft = useCallback((): T | null => {
    return localStore.getJson<T | null>(`${STORAGE_KEYS.editorDraft}:${scope}`, null)
  }, [scope])

  return { state, flush, retry: flush, recoverLocalDraft }
}

import { env } from '@/shared/config/env'
import { logger } from '@/shared/lib/logger'
import { detectPushPlatform, supportsPush } from '@/shared/lib/platform'
import type { PushPlatform } from '@/shared/types/enums'

/**
 * 웹푸시 클라이언트 — 프런트엔드 아키텍처 문서 §10.3
 *
 * `httpClient` 밖에서 브라우저 API를 다루는 예외 모듈 중 하나다(§7.1).
 * 구독 흐름: iOS·비standalone이면 홈 화면 안내 먼저 → 권한 요청 → 구독 → 서버 등록.
 * **거부되면 다시 묻지 않는다.**
 */

export type PushSubscriptionInfo = {
  endpointHash: string
  platform: PushPlatform
}

export type PermissionResult = 'granted' | 'denied' | 'unsupported'

export function currentPermission(): NotificationPermission | 'unsupported' {
  if (!supportsPush()) return 'unsupported'
  return Notification.permission
}

export async function requestPermission(): Promise<PermissionResult> {
  if (!supportsPush()) return 'unsupported'
  const result = await Notification.requestPermission()
  return result === 'granted' ? 'granted' : 'denied'
}

/** endpoint 원문은 서버에 왕복시키지 않는다. SHA-256 해시로만 대조한다(API 문서 §8.5). */
async function hashEndpoint(endpoint: string): Promise<string> {
  const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(endpoint))
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(normalized)
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index)
  return bytes
}

/**
 * 브라우저 구독을 만든다.
 * 서비스워커나 VAPID 키가 없는 환경(데모·개발)에서는 합성 endpoint를 돌려주어
 * 화면 흐름을 끝까지 확인할 수 있게 한다.
 */
export async function subscribe(): Promise<PushSubscriptionInfo | null> {
  const platform = detectPushPlatform()

  if (!supportsPush() || !env.vapidPublicKey) {
    // [MOCK] 실제 배포에서는 VAPID 키가 반드시 존재한다. 없으면 알림 기능을 비활성화한다.
    logger.warn('push unavailable — synthetic subscription for demo')
    return { endpointHash: await hashEndpoint(`demo:${platform}:${navigator.userAgent}`), platform }
  }

  try {
    const registration = await navigator.serviceWorker.ready
    const existing = await registration.pushManager.getSubscription()
    const subscription =
      existing ??
      (await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(env.vapidPublicKey),
      }))
    return { endpointHash: await hashEndpoint(subscription.endpoint), platform }
  } catch (error) {
    logger.warn('push subscribe failed', error)
    return null
  }
}

export async function unsubscribe(): Promise<void> {
  if (!supportsPush()) return
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    await subscription?.unsubscribe()
  } catch (error) {
    logger.warn('push unsubscribe failed', error)
  }
}

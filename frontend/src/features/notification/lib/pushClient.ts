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
  /** 푸시 서비스 endpoint 원문. 서버 등록에만 쓰고 화면에 노출하지 않는다. */
  endpoint: string
  /** 서버 목록과 대조하는 열쇠. 서버는 endpoint 원문을 되돌려주지 않는다(API 문서 §8.5). */
  endpointHash: string
  keys: { p256dh: string; auth: string }
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

/** endpoint 원문은 대조에 쓰지 않는다. SHA-256 해시로만 맞춰 본다(API 문서 §8.5). */
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

/** `ArrayBuffer` 키를 서버가 받는 base64url 문자열로 만든다. */
function toBase64Url(buffer: ArrayBuffer | null): string | null {
  if (!buffer) return null
  let binary = ''
  for (const byte of new Uint8Array(buffer)) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * 브라우저 구독을 만든다.
 *
 * VAPID 공개키가 없거나 브라우저가 푸시를 지원하지 않으면 **구독하지 않는다.**
 * 서버에 등록할 수 없는 구독을 만들어 봐야 알림이 오지 않으므로, 없는 것이 정직하다.
 */
export async function subscribe(): Promise<PushSubscriptionInfo | null> {
  if (!supportsPush() || !env.vapidPublicKey) {
    logger.warn('push unavailable — VAPID key missing or unsupported browser')
    return null
  }

  const platform = detectPushPlatform()

  try {
    const registration = await navigator.serviceWorker.ready
    const existing = await registration.pushManager.getSubscription()
    const subscription =
      existing ??
      (await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(env.vapidPublicKey),
      }))

    const p256dh = toBase64Url(subscription.getKey('p256dh'))
    const auth = toBase64Url(subscription.getKey('auth'))
    if (!p256dh || !auth) {
      logger.warn('push subscription has no encryption keys')
      return null
    }

    return {
      endpoint: subscription.endpoint,
      endpointHash: await hashEndpoint(subscription.endpoint),
      keys: { p256dh, auth },
      platform,
    }
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

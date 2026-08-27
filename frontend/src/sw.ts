/// <reference lib="WebWorker" />

import { clientsClaim } from 'workbox-core'
import { ExpirationPlugin } from 'workbox-expiration'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst } from 'workbox-strategies'

// 알림 문구도 사용자 문구다. 워커라고 예외를 두지 않는다(프런트 §16).
import { push } from '@/shared/config/messages'

/**
 * 서비스워커 — 프런트엔드 아키텍처 문서 §10
 *
 * 이 파일은 **런타임 캐시 전략(§10.1)과 푸시 핸들러(§10.4)만** 담는다.
 * 프리캐시 목록은 Workbox가 빌드 시 `self.__WB_MANIFEST`에 주입한다 —
 * 캐시 이름·해시·정리 로직을 손으로 쓰지 않는다(기술 선택 §2 "서비스워커 수기 작성 금지").
 *
 * 이 파일은 **DOM이 아니라 WebWorker 전역**에서 돈다. 타입 경계는
 * `tsconfig.worker.json`이 따로 갖는다.
 */

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<{ url: string; revision: string | null }>
}

// ── 프리캐시: 앱 셸 ─────────────────────────────────────────────────────
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

/**
 * SPA 내비게이션은 전부 `index.html`로 되돌린다.
 * 단, API와 미디어는 문서 요청이 아니므로 제외한다.
 */
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('index.html'), {
    denylist: [/^\/api\//, /^\/media\//],
  }),
)

// ── 런타임 캐시 (§10.1) ─────────────────────────────────────────────────

/** 폰트 — 1년. 자체 호스팅이므로 파일명이 바뀌면 새 항목이 된다. */
registerRoute(
  ({ request }) => request.destination === 'font',
  new CacheFirst({
    cacheName: 'gk-fonts',
    plugins: [new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 365, maxEntries: 8 })],
  }),
)

/**
 * 작품 이미지 — 30일 / 최대 200개.
 * 서명 URL의 쿼리스트링이 갱신돼도 같은 그림이므로 쿼리를 뺀 경로로 캐시를 맞춘다.
 */
registerRoute(
  ({ url, request }) => url.pathname.startsWith('/media/artworks/') && request.method === 'GET',
  new CacheFirst({
    cacheName: 'gk-artwork-media',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({
        maxAgeSeconds: 60 * 60 * 24 * 30,
        maxEntries: 200,
        purgeOnQuotaError: true,
      }),
    ],
    matchOptions: { ignoreSearch: true },
  }),
)

/** 전시 데이터 — 네트워크 우선, 3초 안에 응답이 없으면 캐시로 (오프라인 렌더의 원천) */
const exhibitionCache = new NetworkFirst({
  cacheName: 'gk-exhibitions',
  networkTimeoutSeconds: 3,
  plugins: [
    new CacheableResponsePlugin({ statuses: [200] }),
    new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 7, maxEntries: 40 }),
  ],
})

/** `/exhibitions/current`와 `/exhibitions/{date}`. 아카이브 목록(`/exhibitions?…`)은 제외한다. */
registerRoute(
  ({ url, request }) =>
    request.method === 'GET' && /\/api\/exhibitions\/[^/]+$/.test(url.pathname),
  exhibitionCache,
)

/** 첫 화면 — 데이터가 없어도 화면은 떠야 하므로 더 짧게 기다린다(FA-7). */
registerRoute(
  ({ url, request }) => request.method === 'GET' && url.pathname.endsWith('/api/public/landing'),
  new NetworkFirst({
    cacheName: 'gk-landing',
    networkTimeoutSeconds: 2,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24, maxEntries: 2 }),
    ],
  }),
)

// 그 밖의 API는 캐시하지 않는다(NetworkOnly = 라우트를 등록하지 않는 것과 같다).

// ── 업데이트 처리 (§10.2) ───────────────────────────────────────────────

/**
 * **즉시 갱신하지 않는다.** 새 워커는 대기 상태로 두고, 화면이 안내 바를 띄운다.
 * 사용자가 `새로고침`을 누를 때만 이 메시지가 온다.
 * 그림을 보는 도중에 화면이 리로드되는 일이 없어야 한다.
 */
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    void self.skipWaiting()
  }
})

clientsClaim()

// ── 푸시 (§10.4) ────────────────────────────────────────────────────────

/** 페이로드가 깨져도 알림은 뜬다. 아침 알림을 통째로 잃는 것보다 낫다. */
type PushPayload = {
  title?: string
  body?: string
  url?: string
  tag?: string
}

const FALLBACK_NOTIFICATION = {
  title: push.fallbackTitle,
  body: push.fallbackBody,
} as const

self.addEventListener('push', (event: PushEvent) => {
  let payload: PushPayload = {}
  try {
    payload = (event.data?.json() as PushPayload) ?? {}
  } catch {
    payload = {}
  }

  const title = payload.title ?? FALLBACK_NOTIFICATION.title
  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body ?? FALLBACK_NOTIFICATION.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      // 같은 태그의 알림은 겹쳐 쌓이지 않는다. 하루 1회 알림이 밀리면 안 된다.
      tag: payload.tag ?? 'gk-daily',
      data: { url: payload.url ?? '/' },
    }),
  )
})

/**
 * **모든 진입은 A 첫 화면을 거친다**(PRD §6.12).
 * 이미 열린 탭이 있으면 새 탭을 만들지 않고 그 탭을 옮긴다.
 */
self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const target = (event.notification.data as { url?: string } | undefined)?.url ?? '/'

  event.waitUntil(
    (async () => {
      const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of clientList) {
        if (new URL(client.url).origin !== self.location.origin) continue
        await client.focus()
        if ('navigate' in client) await client.navigate(target)
        return
      }
      await self.clients.openWindow(target)
    })(),
  )
})

/**
 * 브라우저가 구독을 스스로 교체한 경우.
 * 서버 등록은 인증이 필요하므로 워커가 직접 호출하지 않고, 열린 탭에 알려 재등록시킨다.
 * 열린 탭이 없으면 다음 부팅의 구독 재검증(§10.3)이 같은 일을 한다.
 */
self.addEventListener('pushsubscriptionchange', (event: Event) => {
  const extendable = event as ExtendableEvent
  extendable.waitUntil(
    (async () => {
      const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of clientList) {
        client.postMessage({ type: 'PUSH_SUBSCRIPTION_CHANGED' })
      }
    })(),
  )
})

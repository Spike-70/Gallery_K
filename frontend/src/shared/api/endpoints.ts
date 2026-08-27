import type { IsoDate, Uuid } from '@/shared/types/utility'

/**
 * 엔드포인트 경로 상수 — API 명세서 §4
 * 경로 문자열을 사용처에서 조립하지 않는다.
 */
export const endpoints = {
  public: {
    landing: () => '/public/landing',
    notice: () => '/public/notice',
  },

  auth: {
    signup: () => '/auth/signup',
    login: () => '/auth/login',
    logout: () => '/auth/logout',
    session: () => '/auth/session',
    password: () => '/auth/password',
    passwordResetRequest: () => '/auth/password/reset/request',
    passwordResetConfirm: () => '/auth/password/reset/confirm',

    /**
     * 소셜 로그인 — API 명세서 §6.11–§6.15
     *
     * `socialStart`만 **절대 경로**다. 나머지와 달리 `httpClient`를 타지 않고
     * `<a href>`의 목적지가 되기 때문이다 — 브라우저가 직접 이동해야 리다이렉트
     * 방식이 성립한다(소셜 문서 SA-1).
     */
    socialProviders: () => '/auth/social/providers',
    socialLink: () => '/auth/social/link',
    socialSignup: () => '/auth/social/signup',
  },

  exhibitions: {
    current: () => '/exhibitions/current',
    byDate: (date: IsoDate) => `/exhibitions/${date}`,
    archive: () => '/exhibitions',
    view: (date: IsoDate) => `/exhibitions/${date}/view`,
  },

  artworks: {
    detail: (id: Uuid) => `/artworks/${id}`,
    view: (id: Uuid) => `/artworks/${id}/view`,
  },

  me: {
    root: () => '/me',
    settings: () => '/me/settings',
    pushSubscriptions: () => '/me/push-subscriptions',
    pushSubscription: (id: Uuid) => `/me/push-subscriptions/${id}`,
    socialIdentities: () => '/me/social-identities',
    socialIdentity: (id: Uuid) => `/me/social-identities/${id}`,
  },

  admin: {
    summary: () => '/admin/summary',
    calendar: () => '/admin/exhibitions/calendar',
    exhibition: (date: IsoDate) => `/admin/exhibitions/${date}`,
    exhibitionHide: (date: IsoDate) => `/admin/exhibitions/${date}/hide`,
    exhibitionUnhide: (date: IsoDate) => `/admin/exhibitions/${date}/unhide`,
    exhibitionCarryDraft: (date: IsoDate) => `/admin/exhibitions/${date}/carry-draft`,
    exhibitionPreview: (date: IsoDate) => `/admin/exhibitions/${date}/preview`,
    artworkSlot: (date: IsoDate, position: number) => `/admin/exhibitions/${date}/artworks/${position}`,
    artworkReorder: (date: IsoDate) => `/admin/exhibitions/${date}/artworks/reorder`,
    uploadUrls: (date: IsoDate) => `/admin/exhibitions/${date}/artworks/upload-urls`,
    imageComplete: (artworkId: Uuid) => `/admin/artworks/${artworkId}/image/complete`,

    members: () => '/admin/members',
    memberBlock: (id: Uuid) => `/admin/members/${id}/block`,
    memberUnblock: (id: Uuid) => `/admin/members/${id}/unblock`,
    memberResetPassword: (id: Uuid) => `/admin/members/${id}/reset-password`,

    settings: () => '/admin/settings',
    notices: () => '/admin/notices',
    notice: (id: Uuid) => `/admin/notices/${id}`,

    statsDaily: () => '/admin/stats/daily',
    statsMembers: () => '/admin/stats/members',
    statsMember: (id: Uuid) => `/admin/stats/members/${id}`,
  },

  system: {
    health: () => '/system/health',
  },
} as const

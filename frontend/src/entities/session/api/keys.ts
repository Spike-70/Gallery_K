/** 세션 쿼리 키 — 프런트엔드 아키텍처 문서 §7.3. 키를 사용처에서 조립하지 않는다. */
export const sessionKeys = {
  all: ['session'] as const,
  session: () => ['session'] as const,
  me: () => ['me'] as const,
  /** 켜진 소셜 제공자. 배포 중에는 바뀌지 않으므로 오래 캐시한다 */
  socialProviders: () => ['session', 'social', 'providers'] as const,
  socialIdentities: () => ['session', 'social', 'identities'] as const,
}

/** 세션 쿼리 키 — 프런트엔드 아키텍처 문서 §7.3. 키를 사용처에서 조립하지 않는다. */
export const sessionKeys = {
  all: ['session'] as const,
  session: () => ['session'] as const,
  me: () => ['me'] as const,
}

import { isProduction } from '@/shared/config/env'

/**
 * 로거 — 프런트엔드 아키텍처 문서 §12
 * 프로덕션 빌드에서는 no-op다. 콘솔에 전화번호·이름을 남기지 않는다.
 */
type LogFn = (...args: unknown[]) => void

const noop: LogFn = () => {}

export const logger = {
  debug: isProduction ? noop : (...args: unknown[]) => console.debug('[gk]', ...args),
  info: isProduction ? noop : (...args: unknown[]) => console.info('[gk]', ...args),
  warn: isProduction ? noop : (...args: unknown[]) => console.warn('[gk]', ...args),
  error: (...args: unknown[]) => console.error('[gk]', ...args),
}

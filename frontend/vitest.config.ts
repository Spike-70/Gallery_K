import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

/**
 * 테스트 설정 — 프런트엔드 아키텍처 문서 §14
 *
 * Vitest가 자체 Vite를 번들하므로 `vite.config.ts`에 `test` 키를 섞지 않고 분리한다.
 * 별칭만 같은 규칙으로 유지한다.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    // `stubApi`가 `fetch`를 갈아 끼운다. 테스트마다 원래대로 되돌린다.
    unstubGlobals: true,
    restoreMocks: true,
  },
})

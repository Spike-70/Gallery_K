import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/**
 * Vite 설정 — 프런트엔드 아키텍처 문서 §15
 *
 * - 절대 경로 별칭(`@/app`, `@/features`, `@/entities`, `@/shared`)은 레이어 규칙(§4)을
 *   import 문에서 눈으로 확인할 수 있게 한다.
 * - 청크 분할은 §5.4의 예산 표를 그대로 표현한다.
 *   특히 **관리자 코드는 관람자 경로로 절대 흘러들지 않는다**.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        /**
         * 청크 분할 — 프런트엔드 아키텍처 문서 §5.4
         * Rolldown의 `codeSplitting`으로 §5.4의 예산 표를 그대로 표현한다.
         */
        codeSplitting: {
          groups: [
            { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/ },
            { name: 'vendor-query', test: /node_modules[\\/]@tanstack[\\/]/ },
            // 폼 스택은 A-1·D와 관리자 편집이 함께 쓴다. 한 청크로 모아 중복을 막는다.
            { name: 'vendor-forms', test: /node_modules[\\/](zod|react-hook-form|@hookform)[\\/]/ },
            { name: 'vendor-common', test: /node_modules/ },
            // 관리자 코드는 관람자 경로에서 절대 로드되지 않는다(F-8).
            { name: 'admin', test: /src[\\/]features[\\/]admin[\\/]/ },
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    // 백엔드 연동 시: 동일 오리진 규약(API 문서 §2.11)을 로컬에서도 재현한다.
    // proxy: {
    //   '/api': { target: 'http://localhost:8000', changeOrigin: true },
    // },
  },
})

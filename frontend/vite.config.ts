import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

import { bundleManifest } from './scripts/bundle-manifest-plugin.mjs'

/**
 * Vite 설정 — 프런트엔드 아키텍처 문서 §15
 *
 * - 절대 경로 별칭(`@/app`, `@/features`, `@/entities`, `@/shared`)은 레이어 규칙(§4)을
 *   import 문에서 눈으로 확인할 수 있게 한다.
 * - 청크 분할은 §5.4의 예산 표를 그대로 표현한다.
 *   특히 **관리자 코드는 관람자 경로로 절대 흘러들지 않는다**.
 * - PWA는 `injectManifest`로 붙인다(§10). 프리캐시 목록만 Workbox가 주입하고,
 *   전략과 푸시 핸들러는 `src/sw.ts`가 갖는다.
 */
export default defineConfig({
  plugins: [
    react(),
    // 청크↔모듈 대응을 기록한다. `scripts/check-bundle.mjs`가 이것으로 F-8을 검사한다.
    bundleManifest(),
    VitePWA({
      /**
       * 새 버전을 **즉시 적용하지 않는다**(§10.2). 화면이 안내 바를 띄우고
       * 사용자가 누를 때 갱신한다 — 그림을 보는 도중에 리로드되면 안 된다.
       */
      registerType: 'prompt',
      // 등록은 `app/pwa/registerServiceWorker.ts`가 명시적으로 한다.
      injectRegister: null,
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      // 매니페스트는 `public/manifest.webmanifest`가 단일 원천이다(§10.5).
      manifest: false,
      injectManifest: {
        /**
         * 폰트(woff2)는 프리캐시하지 않는다. 603KB를 설치 시점에 한꺼번에 받으면
         * 첫 방문이 느려진다. `index.html`의 `preload`가 어차피 첫 로드에 받아가고,
         * 워커의 `gk-fonts` 런타임 캐시(CacheFirst · 1년)가 그 응답을 잡아 둔다(§10.1).
         */
        globPatterns: ['**/*.{js,css,html,svg}'],
        globIgnores: [
          // 아이콘·robots는 프리캐시하지 않는다. 설치 시점에만 필요하다.
          '**/icons/*',
          '**/robots.txt',
          // **관리자 청크를 관람자 단말에 미리 내려받지 않는다**(§5.4).
          // 프리캐시는 지연 로드보다 앞서 받으므로, 여기서 빼지 않으면 청크 분리가 무의미해진다.
          'assets/admin-*.js',
        ],
      },
      devOptions: {
        // 개발 중에도 설치·푸시 흐름을 실제로 확인할 수 있어야 한다.
        enabled: true,
        type: 'module',
        navigateFallback: 'index.html',
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      /**
       * `includeDependenciesRecursively: false`(아래)를 쓰면 순환 청크가 생길 수 있다.
       * Rolldown 문서가 지정한 짝 설정으로 실행 순서를 고정해 이를 막는다.
       */
      preserveEntrySignatures: 'allow-extension',
      output: {
        strictExecutionOrder: true,
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
            /**
             * 관리자 코드는 관람자 경로에서 절대 로드되지 않는다(F-8).
             *
             * `includeDependenciesRecursively: false`가 **이 그룹의 핵심**이다.
             * 기본값(true)이면 관리자 화면이 의존하는 것까지 전부 이 청크로 빨려 들어온다 —
             * 미리보기가 관람자 컴포넌트를 재사용하므로(§8.4) 결국 앱 전체가 `admin`이 되고,
             * 관람자가 첫 화면에서 관리자 청크를 통째로 받게 된다. 정확히 F-8이 막으려는 일이다.
             * 공용 의존성은 자동 분할에 맡긴다. `scripts/check-bundle.mjs`가 이것을 검사한다.
             */
            {
              name: 'admin',
              test: /src[\\/]features[\\/]admin[\\/]/,
              includeDependenciesRecursively: false,
            },
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    /**
     * 동일 오리진 규약(API 문서 §2.11)을 로컬에서도 재현한다.
     *
     * 프런트는 5173, `chalice local`은 8000에서 뜨지만 브라우저에는 한 오리진으로 보인다.
     * 그래야 세션 쿠키(`SameSite=Lax`)와 CSRF 헤더가 **배포와 같은 조건에서** 검증된다.
     *
     * 접두를 떼는 이유 — `/api`는 CloudFront가 붙이는 배포 경로이고, `chalice local`의
     * 라우트에는 그 접두가 없다(백엔드 README).
     */
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

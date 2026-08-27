import { relative } from 'node:path'

/**
 * 번들 구성표 기록 플러그인 — `scripts/check-bundle.mjs`의 입력을 만든다.
 *
 * 청크가 **어떤 소스 모듈로 이루어졌는지**는 번들러만 안다. 최소화된 출력물을
 * 정규식으로 훑어 추측하면 청크 이름이 바뀔 때마다 검사가 틀린다.
 * 그래서 빌드 시점에 사실을 그대로 받아 적는다.
 */
export function bundleManifest({ fileName = '.bundle-manifest.json' } = {}) {
  return {
    name: 'gk:bundle-manifest',
    apply: 'build',
    generateBundle(_options, bundle) {
      const root = process.cwd()
      const chunks = {}
      let entry = null

      for (const [name, item] of Object.entries(bundle)) {
        if (item.type !== 'chunk') continue
        if (item.isEntry) entry = name
        chunks[name] = {
          isEntry: Boolean(item.isEntry),
          // 정적 import — 이 청크를 받으면 **반드시 함께 받는** 청크들
          imports: item.imports ?? [],
          // 동적 import — 필요할 때만 받는 청크들
          dynamicImports: item.dynamicImports ?? [],
          modules: (item.moduleIds ?? [])
            .filter((id) => !id.startsWith('\0'))
            .map((id) => relative(root, id).replaceAll('\\', '/')),
        }
      }

      this.emitFile({ type: 'asset', fileName, source: JSON.stringify({ entry, chunks }, null, 2) })
    },
  }
}

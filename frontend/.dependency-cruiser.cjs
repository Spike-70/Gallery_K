/**
 * 레이어 의존 규칙 — 프런트엔드 아키텍처 문서 §4
 *
 * 의존은 한 방향이다: `app → features → entities → shared`.
 * 아래 5개 규칙이 CI에서 실패시킨다. 린트로 표현되지 않는 규칙이라 별도 도구를 쓴다.
 */
module.exports = {
  forbidden: [
    {
      name: 'no-cross-feature',
      comment:
        '기능 간 상호 참조 금지. 공통이 필요하면 entities 또는 shared로 올린다. ' +
        '예외는 관리자 미리보기가 관람자 화면을 재사용하는 경로뿐이다(§8.4).',
      severity: 'error',
      from: { path: '^src/features/([^/]+)/' },
      to: {
        path: '^src/features/([^/]+)/',
        pathNot: [
          '^src/features/$1/',
          // 미리보기 → 갤러리 공개 표면 (프런트 §8.4에서 명시적으로 허용)
          '^src/features/gallery/index\\.ts$',
          // 가입 완료 직후 알림 안내 (UX §3.3의 정해진 흐름)
          '^src/features/notification/index\\.ts$',
        ],
      },
    },
    {
      name: 'no-entities-to-features',
      comment: 'entities는 features를 알지 못한다.',
      severity: 'error',
      from: { path: '^src/entities/' },
      to: { path: '^src/(features|app)/' },
    },
    {
      name: 'no-shared-to-upper',
      comment: 'shared는 상위 레이어를 알지 못한다.',
      severity: 'error',
      from: { path: '^src/shared/' },
      to: { path: '^src/(features|entities|app)/' },
    },
    {
      name: 'no-deep-feature-import',
      comment: '다른 기능의 내부 파일을 깊게 참조하지 않는다. index.ts 경유만 허용한다.',
      severity: 'error',
      from: { pathNot: '^src/features/' },
      // 관리자 기능은 한 단계 더 중첩되어 있으므로(`features/admin/{화면}/`) 두 형태를 모두 허용한다.
      to: {
        path: '^src/features/[^/]+/.+',
        pathNot: ['^src/features/[^/]+/index\\.ts$', '^src/features/admin/[^/]+/index\\.ts$'],
      },
    },
    {
      name: 'no-circular',
      comment: '순환 의존 금지.',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    exclude: { path: '(^src/test/|\\.test\\.tsx?$)' },
    tsConfig: { fileName: './tsconfig.app.json' },
    tsPreCompilationDeps: true,
    enhancedResolveOptions: { extensions: ['.ts', '.tsx', '.js'] },
  },
}

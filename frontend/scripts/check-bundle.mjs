/**
 * 번들 예산·격리 검사 — 프런트엔드 아키텍처 문서 §5.4 · §15.2
 *
 *   node scripts/check-bundle.mjs      (npm run build 끝에 자동 실행)
 *
 * 두 가지를 **빌드 실패로** 강제한다.
 *
 *  1. **관리자 청크 격리** — 관람자가 첫 화면에서 받는 청크에 관리자 코드가 한 모듈이라도
 *     섞이면 실패한다. `RequireCurator` 아래 `lazy()`라는 규칙은 코드를 읽어야만 지켜졌는지
 *     알 수 있다. 산출물을 직접 보는 검사만이 이것을 사고로부터 지킨다(F-8).
 *
 *  2. **청크 예산** — §5.4의 gzip 목표를 넘으면 실패한다.
 *
 * 판단 근거는 `dist/.bundle-manifest.json`(번들러가 기록한 청크↔모듈 대응)이다.
 * 최소화된 출력물을 정규식으로 추측하지 않는다.
 *
 * 레이어 규칙을 dependency-cruiser가 지키듯, 청크 규칙은 이 스크립트가 지킨다.
 */
import { gzipSync } from 'node:zlib'
import { readFileSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DIST = resolve(ROOT, 'dist')
const MANIFEST = resolve(DIST, '.bundle-manifest.json')

if (!existsSync(MANIFEST)) {
  console.error(`${MANIFEST} 가 없습니다. 먼저 npm run build 를 실행하세요.`)
  process.exit(1)
}

const { entry, chunks } = JSON.parse(readFileSync(MANIFEST, 'utf-8'))

/** 소스 위치로 청크의 성격을 판정한다. 파일명(해시 포함)에 의존하지 않는다. */
const isAdminModule = (id) => id.startsWith('src/features/admin/')
const isVendorModule = (id) => id.includes('node_modules/')
/** C-1·C-3·C-4 — 관람자의 지연 로드 화면 */
const GALLERY_EXTRA = ['src/features/exhibition-theme/', 'src/features/archive/', 'src/features/settings/']

const gzipKb = (name) => gzipSync(readFileSync(resolve(DIST, name)), { level: 9 }).length / 1024
for (const [name, chunk] of Object.entries(chunks)) chunk.gzipKb = gzipKb(name)

// ── 1. 관리자 격리 ──────────────────────────────────────────────────────
/** 엔트리에서 **정적 import 만** 따라간 폐포 = 첫 화면이 반드시 받는 것 */
function staticClosure(from) {
  const seen = new Set()
  const queue = [from]
  while (queue.length > 0) {
    const name = queue.pop()
    if (!name || seen.has(name)) continue
    seen.add(name)
    for (const next of chunks[name]?.imports ?? []) queue.push(next)
  }
  return seen
}

const failures = []
const eager = staticClosure(entry)

for (const name of eager) {
  const leaked = (chunks[name]?.modules ?? []).filter(isAdminModule)
  if (leaked.length > 0) {
    failures.push(
      `관리자 모듈이 첫 화면 청크 ${name} 에 섞였다 (${leaked.length}개, 예: ${leaked[0]})`,
    )
  }
}

const adminChunks = Object.entries(chunks).filter(([, chunk]) => chunk.modules.some(isAdminModule))

/** 관리자 청크가 관람자 전용 청크를 정적으로 끌고 가는 것은 문제가 아니다(그 반대만 문제다). */
for (const [name, chunk] of Object.entries(chunks)) {
  if (chunk.modules.some(isAdminModule)) continue
  if (!eager.has(name)) continue
  const admins = new Set(adminChunks.map(([adminName]) => adminName))
  for (const imported of chunk.imports) {
    if (admins.has(imported)) failures.push(`첫 화면 청크 ${name} 가 관리자 청크 ${imported} 를 정적으로 import 한다`)
  }
}

/**
 * 순환 청크 검사.
 * `includeDependenciesRecursively: false`(vite.config.ts)는 순환 청크를 만들 수 있고,
 * 순환은 평가 순서에 따라 초기화 전 바인딩 접근(TDZ)으로 런타임에 터진다.
 * `strictExecutionOrder`로 막고 있지만, **막혀 있다는 사실 자체를 검사**한다.
 */
{
  const state = new Map()
  const walk = (name, stack) => {
    state.set(name, 'visiting')
    for (const next of chunks[name]?.imports ?? []) {
      if (state.get(next) === 'visiting') {
        const cycle = [...stack.slice(stack.indexOf(next)), next].join(' → ')
        failures.push(`순환 청크: ${cycle}`)
      } else if (!state.has(next)) {
        walk(next, [...stack, next])
      }
    }
    state.set(name, 'done')
  }
  for (const name of Object.keys(chunks)) if (!state.has(name)) walk(name, [name])
}

/**
 * 서비스워커의 프리캐시는 지연 로드보다 **앞서** 받는다.
 * 관리자 청크가 프리캐시 목록에 들어가면 `lazy()` 경계가 있어도 관람자가 통째로 내려받는다.
 * 청크 격리를 우회하는 가장 조용한 경로이므로 여기서 함께 막는다(§10.1).
 */
const swPath = resolve(DIST, 'sw.js')
if (existsSync(swPath)) {
  const sw = readFileSync(swPath, 'utf-8')
  for (const [name] of adminChunks) {
    if (sw.includes(name)) failures.push(`관리자 청크가 서비스워커 프리캐시 목록에 있다: ${name}`)
  }
}

// ── 2. 청크 예산 (§5.4) ─────────────────────────────────────────────────
const sum = (names) => names.reduce((total, name) => total + chunks[name].gzipKb, 0)
const vendorMatching = (pattern) =>
  Object.entries(chunks)
    .filter(([, chunk]) => chunk.modules.some((id) => pattern.test(id)))
    .map(([name]) => name)

const eagerAppChunks = [...eager].filter((name) => !chunks[name].modules.some(isVendorModule))
const galleryExtraChunks = Object.entries(chunks)
  .filter(([name, chunk]) => {
    if (eager.has(name)) return false
    // 화면의 소속은 `features/`가 정한다. 함께 실린 entities·shared는 판정에 넣지 않는다.
    const features = chunk.modules.filter((id) => id.startsWith('src/features/'))
    return features.length > 0 && features.every((id) => GALLERY_EXTRA.some((prefix) => id.startsWith(prefix)))
  })
  .map(([name]) => name)

const GROUPS = [
  { label: 'main (셸·라우터·프로바이더·shared/ui·세션·A·A-1·C·C-2)', names: eagerAppChunks, budgetKb: 60 },
  { label: 'gallery-extra (C-1·C-3·C-4)', names: galleryExtraChunks, budgetKb: 20 },
  { label: 'admin (B 계열 전부)', names: adminChunks.map(([name]) => name), budgetKb: 120 },
  {
    label: 'vendor-react',
    names: vendorMatching(/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//),
    budgetKb: 60,
    /**
     * 알려진 초과. React 19 + React Router 7의 실측 크기이며 코드로 줄일 여지가 없다.
     * 숨기지 않고 **면제로 기록**한다 — 예산을 조용히 올리면 표가 의미를 잃는다.
     */
    waiver: 'React 19 + React Router 7의 실측 크기. 코드로 줄일 수 있는 여지가 없다',
  },
  { label: 'vendor-query', names: vendorMatching(/node_modules\/@tanstack\//), budgetKb: 15 },
]

const report = []
const waived = []
const accounted = new Set()

for (const group of GROUPS) {
  if (group.names.length === 0) continue
  for (const name of group.names) accounted.add(name)
  const totalKb = sum(group.names)
  const over = totalKb > group.budgetKb
  const mark = !over ? '✔' : group.waiver ? '△' : '✖'
  report.push(`  ${mark} ${group.label.padEnd(52)} ${totalKb.toFixed(1).padStart(6)} / ${group.budgetKb} KB`)
  if (over && group.waiver) waived.push(`${group.label} — ${group.waiver}`)
  if (over && !group.waiver) {
    failures.push(`청크 예산 초과: ${group.label} — ${totalKb.toFixed(1)}KB > ${group.budgetKb}KB (gzip)`)
  }
}

console.log('\n번들 예산 (gzip) — 프런트엔드 아키텍처 문서 §5.4')
console.log(report.join('\n'))

const rest = Object.entries(chunks)
  .filter(([name, chunk]) => !accounted.has(name) && chunk.gzipKb >= 1)
  .sort((a, b) => b[1].gzipKb - a[1].gzipKb)
if (rest.length > 0) {
  console.log('\n  예산표에 없는 청크 (참고)')
  for (const [name, chunk] of rest) {
    console.log(`    · ${name.padEnd(50)} ${chunk.gzipKb.toFixed(1).padStart(6)} KB`)
  }
}
if (waived.length > 0) {
  console.log('\n  면제된 초과')
  for (const item of waived) console.log(`    △ ${item}`)
}

if (failures.length > 0) {
  console.error('\n번들 검사 실패')
  for (const failure of failures) console.error(`  ✖ ${failure}`)
  console.error('')
  process.exit(1)
}

console.log(
  `\n  관리자 모듈 ${adminChunks.reduce((n, [, c]) => n + c.modules.filter(isAdminModule).length, 0)}개는 첫 화면 청크 ${eager.size}개 어디에도 없다 ✔\n`,
)

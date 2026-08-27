/**
 * 디자인 토큰·문구 규약 검사 — 디자인 시스템 문서 §11.4 · §12.3, 프런트엔드 §16
 *
 *   node scripts/check-design-tokens.mjs      (npm run verify 에 포함)
 *
 * 문서가 "린트로 차단한다"고 적어 둔 규칙들에는 **실제로 차단하는 코드가 있어야 한다.**
 * 없으면 규칙이 아니라 희망이다. 이 스크립트가 그 차단기다.
 *
 *  1. 임의 값 금지            `text-[13px]` `p-[7px]`        (DS-7)
 *  2. 원시 색 변수 직접 참조 금지 `var(--gk-neutral-700)`      (§2.1 2계층 우회)
 *  3. 하드코딩 색상값 금지      `#8a8a8a` `rgb(...)`          (§12.3-c)
 *  4. `z-[숫자]` 금지                                        (§5.5)
 *  5. 인라인 `style` 금지 (예외 3곳)                          (§11.4)
 *  6. 스케일 밖 간격 유틸 금지  `h-7` `w-32`                   ← CSS가 생성되지 않는다
 *  7. JSX 한국어 문자열 금지    문구는 `messages.ts` 하나에    (프런트 §16)
 *  8. 명도 대비 검증                                         (§3.3, §12.3-a)
 *  9. 미사용 의미 토큰 검출                                   (§12.3-b)
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, extname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SRC = resolve(ROOT, 'src')

// ── 명시적 예외 ─────────────────────────────────────────────────────────
/** DS-7이 인정하는 유일한 임의 값: 그림의 종횡비. 여기에 레이아웃 템플릿을 더한다. */
const ARBITRARY_ALLOWED = [/^aspect-\[/, /^grid-cols-\[/, /^grid-rows-\[/]

/** 인라인 `style`이 허용되는 곳 — 종횡비·LQIP·제스처 transform (§11.4) */
const INLINE_STYLE_ALLOWED = new Set([
  'src/entities/artwork/ui/ArtworkImage.tsx',
  'src/features/artwork/components/SwipePager.tsx',
  'src/features/artwork/components/ImmersiveViewer.tsx',
  'src/shared/ui/BottomSheet.tsx',
  'src/shared/ui/PullToRefresh.tsx',
])

/** 색상값이 허용되는 곳 — 데모 그림을 만드는 생성기(UI 색이 아니다) */
const COLOR_ALLOWED = [/^src\/mocks\//]

/** 한국어 문자열이 허용되는 곳 — 문구 원천 자신과 데모 전용 계층 */
const KOREAN_ALLOWED = [
  /^src\/shared\/config\/messages\.ts$/,
  /^src\/shared\/api\/errorMessages\.ts$/, // 오류 코드 폴백 맵 — 문구의 두 번째 원천(§7.2)
  /^src\/features\/auth\/content\/terms\.ts$/,
  /^src\/mocks\//,
  /^src\/features\/auth\/components\/DemoAccountsNotice\.tsx$/, // 데모 전용. 목과 함께 사라진다
  /__tests__/,
  /\.test\.tsx?$/,
  /^src\/test\//,
  /^src\/shared\/lib\/date\.ts$/, // 요일·`분 전` 등 포맷 조각
]

/** `theme.spacing`이 정의하는 값. 이 밖의 숫자는 CSS가 생성되지 않는다. */
const SPACING_KEYS = new Set([
  '0', 'px', '1', '2', '3', '4', '5', '6', '8', '10', '12', '16',
  'touch', 'control-sm', 'control-md', 'control-lg', 'full',
  'switch-track', 'row', 'row-lg', 'block', 'image-preview', 'icon-lg',
])
const SPACING_PROPS =
  '(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|w|h|min-w|min-h|max-w|max-h|top|bottom|left|right|inset|space-x|space-y|size|translate-x|translate-y)'
/** spacing 외의 스케일에서 오는 값들(width의 분수, maxWidth·maxHeight 토큰 등) */
const NON_SPACING_VALUES = new Set([
  'auto', 'screen', 'min', 'max', 'fit', 'none', 'prose',
  'gallery', 'reading', 'studio', 'form', 'preview', 'sheet',
])

const findings = []
const report = (file, line, rule, detail) => findings.push({ file, line, rule, detail })

// ── 파일 수집 ───────────────────────────────────────────────────────────
function walk(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) out.push(...walk(full))
    else if (['.ts', '.tsx'].includes(extname(full))) out.push(full)
  }
  return out
}

/** 주석과 import 문은 규약 검사 대상이 아니다. */
function stripNoise(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, (match) => match.replace(/[^\n]/g, ' '))
    .replace(/(^|[^:])\/\/[^\n]*/g, (match) => match.replace(/[^\n]/g, ' '))
    .split('\n')
    .map((line) => (/^\s*(import|export)\s.*from\s/.test(line) ? '' : line))
    .join('\n')
}

for (const absolute of walk(SRC)) {
  const file = relative(ROOT, absolute).replaceAll('\\', '/')
  const raw = readFileSync(absolute, 'utf-8')
  const source = stripNoise(raw)
  const lines = source.split('\n')

  lines.forEach((text, index) => {
    const line = index + 1

    // 1·4·6. Tailwind 클래스 검사
    for (const match of text.matchAll(/(?<![\w:[-])([a-z][a-z0-9]*(?:-[a-z0-9]+)*)-(\[[^\]]+\]|[a-z0-9/.-]+)/g)) {
      const token = match[0]
      const prop = match[1]
      const value = match[2]

      if (value.startsWith('[')) {
        // ARIA·data 변형(`aria-[current=true]:`)은 값이 아니라 선택자다.
        if (/^(aria|data|supports|has|group|peer)$/.test(prop)) continue
        if (ARBITRARY_ALLOWED.some((allowed) => allowed.test(token))) continue
        if (prop === 'z') report(file, line, 'z-임의값', token)
        else report(file, line, '임의값', token)
        continue
      }

      if (new RegExp(`^${SPACING_PROPS}$`).test(prop)) {
        if (value.includes('/') || NON_SPACING_VALUES.has(value)) continue
        if (!SPACING_KEYS.has(value)) {
          report(file, line, '스케일밖-간격', `${token} → CSS가 생성되지 않는다`)
        }
      }
    }

    // 2. 원시 색 변수 직접 참조
    for (const match of text.matchAll(/var\(--gk-(neutral|accent|success|warning|danger|info|ink)-[\w-]+\)/g)) {
      report(file, line, '원시색-직접참조', match[0])
    }

    // 3. 하드코딩 색상값
    if (!COLOR_ALLOWED.some((allowed) => allowed.test(file))) {
      for (const match of text.matchAll(/#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)/g)) {
        report(file, line, '하드코딩-색상', match[0])
      }
    }

    // 5. 인라인 style
    if (/\bstyle=\{\{/.test(text) && !INLINE_STYLE_ALLOWED.has(file)) {
      report(file, line, '인라인-style', text.trim().slice(0, 60))
    }

    // 7. 한국어 문자열
    // 개발자에게만 보이는 throw 메시지는 사용자 문구가 아니다.
    const isDeveloperThrow = /throw new Error\(/.test(text)
    if (!isDeveloperThrow && !KOREAN_ALLOWED.some((allowed) => allowed.test(file)) && /[가-힣]/.test(text)) {
      report(file, line, '하드코딩-문구', text.trim().slice(0, 70))
    }
  })
}

// ── 8. 명도 대비 (§3.3) ─────────────────────────────────────────────────
const tokensCss = readFileSync(resolve(SRC, 'styles/tokens.css'), 'utf-8')
const rootStart = tokensCss.indexOf(':root')
const rootEnd = tokensCss.indexOf("html[data-font-scale='large']")
const rootBlock = tokensCss.slice(rootStart, rootEnd > rootStart ? rootEnd : undefined)
const declared = new Map()
for (const match of rootBlock.matchAll(/(--gk-[\w-]+)\s*:\s*([^;]+);/g)) {
  declared.set(match[1], match[2].trim())
}

function resolveVar(name, depth = 0) {
  const value = declared.get(name)
  if (value === undefined || depth > 8) return null
  const reference = value.match(/^var\((--gk-[\w-]+)\)$/)
  return reference ? resolveVar(reference[1], depth + 1) : value
}

function toRgb(value) {
  const hex = value.trim()
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return null
  return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16))
}

function luminance(rgb) {
  const [r, g, b] = rgb.map((channel) => {
    const c = channel / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a, b) {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (high + 0.05) / (low + 0.05)
}

/** §3.3 검증 기준 */
const CONTRAST_PAIRS = [
  ['--gk-text-primary', '--gk-bg-canvas', 7],
  ['--gk-text-secondary', '--gk-bg-canvas', 4.5],
  ['--gk-text-tertiary', '--gk-bg-canvas', 4.5],
  ['--gk-text-accent', '--gk-bg-canvas', 4.5],
  ['--gk-action-primary-fg', '--gk-action-primary-bg', 7],
  ['--gk-status-published', '--gk-bg-canvas', 4.5],
  ['--gk-status-empty', '--gk-bg-canvas', 4.5],
  ['--gk-status-carried', '--gk-bg-canvas', 4.5],
  ['--gk-status-info', '--gk-bg-canvas', 4.5],
  ['--gk-action-danger-fg', '--gk-bg-canvas', 4.5],
]

const contrastRows = []
for (const [foreground, background, minimum] of CONTRAST_PAIRS) {
  const fg = toRgb(resolveVar(foreground) ?? '')
  const bg = toRgb(resolveVar(background) ?? '')
  if (!fg || !bg) {
    report('src/styles/tokens.css', 0, '대비-확인불가', `${foreground} on ${background}`)
    continue
  }
  const ratio = contrast(fg, bg)
  contrastRows.push(`  ${ratio >= minimum ? '✔' : '✖'} ${foreground.padEnd(26)} on ${background.padEnd(20)} ${ratio.toFixed(1)}:1 (≥ ${minimum})`)
  if (ratio < minimum) {
    report('src/styles/tokens.css', 0, '대비-미달', `${foreground} on ${background} — ${ratio.toFixed(2)}:1 < ${minimum}`)
  }
}

// ── 9. 미사용 의미 토큰 ─────────────────────────────────────────────────
const allSource = [...walk(SRC)].map((file) => readFileSync(file, 'utf-8')).join('\n')
const configSource = readFileSync(resolve(ROOT, 'tailwind.config.js'), 'utf-8')
const cssSource = ['tokens.css', 'base.css', 'index.css', 'fonts.css']
  .map((name) => readFileSync(resolve(SRC, 'styles', name), 'utf-8'))
  .join('\n')

const unusedTokens = []
for (const name of declared.keys()) {
  // 원시 팔레트는 의미 토큰에 의해서만 쓰이므로 검사 대상이 아니다.
  if (/^--gk-(neutral|accent|success|warning|danger|info|ink)-/.test(name)) continue
  const short = name.replace('--gk-', '')
  const referenced =
    cssSource.split(`${name}:`).length - 1 < cssSource.split(name).length - 1 ||
    configSource.includes(name) ||
    configSource.includes(short.replace(/^(font-size|line-height|letter-spacing|font-weight)-/, '')) ||
    allSource.includes(name)
  if (!referenced) unusedTokens.push(name)
}

// ── 출력 ────────────────────────────────────────────────────────────────
console.log('\n명도 대비 — 디자인 시스템 문서 §3.3')
console.log(contrastRows.join('\n'))

if (unusedTokens.length > 0) {
  console.log(`\n미사용 의미 토큰 ${unusedTokens.length}개 (참고)`)
  console.log(`  ${unusedTokens.join(', ')}`)
}

if (findings.length > 0) {
  const byRule = new Map()
  for (const finding of findings) {
    if (!byRule.has(finding.rule)) byRule.set(finding.rule, [])
    byRule.get(finding.rule).push(finding)
  }
  console.error('\n디자인 규약 위반')
  for (const [rule, items] of byRule) {
    console.error(`\n  [${rule}] ${items.length}건`)
    for (const item of items.slice(0, 12)) {
      console.error(`    ${item.file}:${item.line}  ${item.detail}`)
    }
    if (items.length > 12) console.error(`    … 외 ${items.length - 12}건`)
  }
  console.error('')
  process.exit(1)
}

console.log('\n  디자인 규약 위반 없음 ✔\n')

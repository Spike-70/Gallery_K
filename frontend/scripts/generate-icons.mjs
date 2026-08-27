/**
 * PWA 아이콘 생성 — 프런트엔드 아키텍처 문서 §10.5
 *
 * `public/favicon.svg`와 **같은 도형**을 PNG로 굽는다. 매니페스트 아이콘은 PNG만
 * 신뢰할 수 있고(안드로이드 스플래시·iOS 홈 화면), 저장소에 바이너리를 손으로 넣으면
 * 로고가 바뀔 때 되살릴 방법이 없다. 이 스크립트가 유일한 원천이다.
 *
 *   node scripts/generate-icons.mjs
 *
 * 외부 의존성을 쓰지 않는다(래스터라이저 없이 zlib만으로 PNG를 인코딩한다).
 */
import { deflateSync } from 'node:zlib'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const OUT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../public/icons')

/** 디자인 토큰과 같은 값을 쓴다(tokens.css). */
const COLORS = {
  canvas: [0xfa, 0xf9, 0xf7],
  frame: [0x2a, 0x27, 0x24],
  accent: [0x8c, 0x6a, 0x3f],
  ink: [0x40, 0x3c, 0x36],
}

// ── 도형 (favicon.svg의 32×32 좌표계 그대로) ────────────────────────────
const roundedRect = (x, y, w, h, r) => (px, py) => {
  if (px < x || py < y || px > x + w || py > y + h) return false
  const cx = Math.min(Math.max(px, x + r), x + w - r)
  const cy = Math.min(Math.max(py, y + r), y + h - r)
  return (px - cx) ** 2 + (py - cy) ** 2 <= r * r
}
const rect = (x, y, w, h) => (px, py) => px >= x && py >= y && px <= x + w && py <= y + h
const strokedRect = (x, y, w, h, width) => {
  const outer = rect(x - width / 2, y - width / 2, w + width, h + width)
  const inner = rect(x + width / 2, y + width / 2, w - width, h - width)
  return (px, py) => outer(px, py) && !inner(px, py)
}
const circle = (cx, cy, r) => (px, py) => (px - cx) ** 2 + (py - cy) ** 2 <= r * r
const polygon = (points) => (px, py) => {
  let inside = false
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const [xi, yi] = points[i]
    const [xj, yj] = points[j]
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/** 액자 하나 — UI는 액자다(제품 원칙 4). */
const ARTWORK = [
  { shape: strokedRect(7, 6, 18, 20, 1.6), color: COLORS.frame },
  { shape: circle(13, 13, 2.2), color: COLORS.accent },
  {
    shape: polygon([
      [9, 22],
      [14, 16],
      [17.5, 19.5],
      [20, 17],
      [23, 22],
    ]),
    color: COLORS.ink,
  },
]

const SUPERSAMPLE = 4

/**
 * @param {number} size      출력 픽셀 크기
 * @param {number} inset     0=전면, 0.1=가장자리 10%를 비움(maskable 안전 영역)
 * @param {number} cornerR   32좌표계 기준 모서리 반경. 0이면 사각(플랫폼이 직접 마스킹)
 */
function render(size, { inset = 0, cornerR = 0 } = {}) {
  const scale = size / 32
  const artScale = 1 - inset * 2
  const offset = (32 * inset) / artScale
  const layers = [
    { shape: cornerR > 0 ? roundedRect(0, 0, 32, 32, cornerR) : rect(0, 0, 32, 32), color: COLORS.canvas, full: true },
    ...ARTWORK,
  ]

  const pixels = Buffer.alloc(size * size * 4)
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      let r = 0
      let g = 0
      let b = 0
      let a = 0
      for (let sy = 0; sy < SUPERSAMPLE; sy += 1) {
        for (let sx = 0; sx < SUPERSAMPLE; sx += 1) {
          const px = (x + (sx + 0.5) / SUPERSAMPLE) / scale
          const py = (y + (sy + 0.5) / SUPERSAMPLE) / scale
          for (let index = layers.length - 1; index >= 0; index -= 1) {
            const layer = layers[index]
            // 배경은 캔버스 전체 좌표, 그림은 안전 영역 안으로 축소된 좌표에서 검사한다.
            const [tx, ty] = layer.full ? [px, py] : [px / artScale - offset, py / artScale - offset]
            if (layer.shape(tx, ty)) {
              r += layer.color[0]
              g += layer.color[1]
              b += layer.color[2]
              a += 255
              break
            }
          }
        }
      }
      const samples = SUPERSAMPLE * SUPERSAMPLE
      const base = (y * size + x) * 4
      // 커버리지가 0인 픽셀은 완전 투명. 색을 커버리지로 나눠 프리멀티플라이를 푼다.
      const coverage = a / 255
      pixels[base] = coverage ? Math.round(r / coverage) : 0
      pixels[base + 1] = coverage ? Math.round(g / coverage) : 0
      pixels[base + 2] = coverage ? Math.round(b / coverage) : 0
      pixels[base + 3] = Math.round(a / samples)
    }
  }
  return pixels
}

// ── PNG 인코딩 (RGBA8, 필터 0) ──────────────────────────────────────────
function crc32(buffer) {
  let crc = 0xffffffff
  for (const byte of buffer) {
    crc ^= byte
    for (let bit = 0; bit < 8; bit += 1) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1
  }
  return (crc ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data])
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(body))
  return Buffer.concat([length, body, crc])
}

function encodePng(size, pixels) {
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8 // bit depth
  ihdr[9] = 6 // color type: RGBA
  const raw = Buffer.alloc(size * (size * 4 + 1))
  for (let y = 0; y < size; y += 1) {
    raw[y * (size * 4 + 1)] = 0
    pixels.copy(raw, y * (size * 4 + 1) + 1, y * size * 4, (y + 1) * size * 4)
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

const TARGETS = [
  { file: 'icon-192.png', size: 192, options: { cornerR: 6 } },
  { file: 'icon-512.png', size: 512, options: { cornerR: 6 } },
  // maskable: 플랫폼이 임의 모양으로 잘라내므로 전면 배경 + 안전 영역(80%) 안의 그림.
  { file: 'icon-maskable-512.png', size: 512, options: { inset: 0.1 } },
  // iOS 홈 화면. iOS가 직접 모서리를 깎으므로 사각으로 굽는다(PRD §6.4의 홈 화면 추가 안내).
  { file: 'apple-touch-icon.png', size: 180, options: {} },
]

mkdirSync(OUT_DIR, { recursive: true })
for (const { file, size, options } of TARGETS) {
  writeFileSync(resolve(OUT_DIR, file), encodePng(size, render(size, options)))
  console.log(`generated  public/icons/${file}  (${size}×${size})`)
}

import type { RawImageSet } from '@/shared/api/types'

import { seededRandom } from '@/mocks/lib/mockClient'

/**
 * 그림 이미지 생성기 — 데모 전용
 *
 * 외부 이미지 호스트를 쓰지 않는다(폐쇄형 원칙, PRD §8.4). 시드로 결정되는 SVG를
 * data URI로 만들어 CDN·서명 쿠키 없이도 12점 그리드가 그대로 보이게 한다.
 * 실제 서비스에서는 이 자리에 CloudFront 경로가 들어온다(API 문서 §3.1).
 */

/** 따뜻한 무채색 배경 위의 저채도 조합. 그림에서 나오는 색이 화면의 유일한 채도다(DS-1). */
const PALETTES = [
  ['#6b7f8c', '#c9b191', '#2f3a42'],
  ['#8c6a3f', '#d9c9a8', '#3b2f24'],
  ['#5c6b52', '#c2c9a8', '#2b3327'],
  ['#7d5b62', '#dcc3bd', '#38262a'],
  ['#4f5f78', '#b8c3d4', '#25303f'],
  ['#8a7645', '#e0d2ae', '#3a3222'],
  ['#5d5a6b', '#c4bfd1', '#2c2a35'],
  ['#7a4f43', '#d6b6a3', '#372220'],
  ['#4a6b63', '#b2cec4', '#22332f'],
  ['#87724f', '#dfd0b4', '#3b3323'],
  ['#63587a', '#c8bed8', '#2f2939'],
  ['#8a5f52', '#e0c2b0', '#3d2822'],
] as const

function svgToDataUri(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg.replace(/\s+/g, ' ').trim())}`
}

function painting(seed: number, width: number, height: number): string {
  const random = seededRandom(seed * 7919 + 13)
  const [base, light, dark] = PALETTES[seed % PALETTES.length]

  const shapes = Array.from({ length: 5 }, (_, index) => {
    const cx = Math.round(random() * width)
    const cy = Math.round(random() * height)
    const r = Math.round((0.18 + random() * 0.34) * Math.min(width, height))
    const fill = index % 2 === 0 ? light : dark
    const opacity = (0.18 + random() * 0.4).toFixed(2)
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" opacity="${opacity}"/>`
  }).join('')

  const horizon = Math.round(height * (0.55 + random() * 0.2))

  return svgToDataUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <defs>
        <linearGradient id="g${seed}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${light}"/>
          <stop offset="100%" stop-color="${base}"/>
        </linearGradient>
        <filter id="b${seed}"><feGaussianBlur stdDeviation="${Math.round(Math.min(width, height) * 0.04)}"/></filter>
      </defs>
      <rect width="${width}" height="${height}" fill="url(#g${seed})"/>
      <g filter="url(#b${seed})">${shapes}</g>
      <rect y="${horizon}" width="${width}" height="${height - horizon}" fill="${dark}" opacity="0.35"/>
    </svg>
  `)
}

/** LQIP — 16px 폭 블러 플레이스홀더(API 문서 §3.1) */
function lqip(seed: number): string {
  const [base, light] = PALETTES[seed % PALETTES.length]
  return svgToDataUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
      <rect width="16" height="16" fill="${light}"/>
      <circle cx="9" cy="10" r="7" fill="${base}" opacity="0.7"/>
    </svg>
  `)
}

/**
 * 한 그림의 이미지 3종 + 메타. 실제 응답과 동일한 `ImageSet` 형태다.
 * `aspect_ratio`는 레이아웃 시프트 방지를 위해 반드시 채운다(§9).
 */
export function createImageSet(seed: number, ratio = 4 / 5): RawImageSet {
  const width = 1600
  const height = Math.round(width / ratio)
  return {
    thumb_url: painting(seed, 400, 400),
    display_url: painting(seed, 800, Math.round(800 / ratio)),
    origin_url: painting(seed, width, height),
    lqip: lqip(seed),
    width,
    height,
    aspect_ratio: Number(ratio.toFixed(4)),
  }
}

/** A 첫 화면의 미술관 정문 이미지(4:3 고정, PRD §6.1) */
export const entranceImageUrl = svgToDataUri(`
  <svg xmlns="http://www.w3.org/2000/svg" width="960" height="720" viewBox="0 0 960 720">
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#e8e2d6"/>
        <stop offset="100%" stop-color="#cfc7b8"/>
      </linearGradient>
    </defs>
    <rect width="960" height="720" fill="url(#sky)"/>
    <rect x="120" y="120" width="720" height="600" fill="#b9b0a1"/>
    <rect x="150" y="150" width="660" height="570" fill="#a79d8d"/>
    <rect x="380" y="330" width="200" height="390" fill="#4a4239"/>
    <path d="M120 120 L480 20 L840 120 Z" fill="#8f8676"/>
    <g fill="#c9c0b0">
      <rect x="210" y="230" width="46" height="490"/>
      <rect x="316" y="230" width="46" height="490"/>
      <rect x="598" y="230" width="46" height="490"/>
      <rect x="704" y="230" width="46" height="490"/>
    </g>
    <rect x="380" y="330" width="200" height="10" fill="#2f2a24"/>
  </svg>
`)

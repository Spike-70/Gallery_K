import forms from '@tailwindcss/forms'

/**
 * TailwindCSS v3 설정 — 디자인 시스템 문서 §11
 *
 * 원칙
 *  - Tailwind는 **의미(semantic) 토큰만** 소비한다. 원시 팔레트는 등록하지 않는다(DS-7).
 *  - `colors`·`fontSize`·`spacing`은 `extend`가 아니라 **덮어쓴다**.
 *    기본 스케일이 남아 있으면 `text-xs`(12px) 같은 금지 값이 쓰인다(DS-3).
 *  - 값의 실체는 `src/styles/tokens.css`의 CSS 변수다. 큰 글씨 모드·몰입 뷰어는
 *    변수 값만 교체되며 컴포넌트 클래스는 한 줄도 바뀌지 않는다.
 */

/** 의미 토큰 색을 CSS 변수로 잇는다. */
const semanticColor = (name) => `var(--gk-${name})`

/** 타입 스케일 한 줄. 크기·행간·자간·굵기 모두 변수를 참조한다(§4.2). */
const typeScale = (name) => [
  `var(--gk-font-size-${name})`,
  {
    lineHeight: `var(--gk-line-height-${name})`,
    letterSpacing: `var(--gk-letter-spacing-${name})`,
    fontWeight: `var(--gk-font-weight-${name})`,
  },
]

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // ── 색: 의미 토큰만 (디자인 문서 §3.2) ───────────────────────────────
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      inherit: 'inherit',

      canvas: semanticColor('bg-canvas'),
      surface: semanticColor('bg-surface'),
      subtle: semanticColor('bg-subtle'),
      overlay: semanticColor('bg-overlay'),

      primary: semanticColor('text-primary'),
      secondary: semanticColor('text-secondary'),
      tertiary: semanticColor('text-tertiary'),
      placeholder: semanticColor('text-placeholder'),
      inverse: semanticColor('text-inverse'),
      accent: semanticColor('text-accent'),
      'accent-subtle': semanticColor('bg-accent-subtle'),

      'border-default': semanticColor('border-default'),
      'border-strong': semanticColor('border-strong'),
      'border-focus': semanticColor('border-focus'),

      'action-primary': semanticColor('action-primary-bg'),
      'action-primary-fg': semanticColor('action-primary-fg'),
      'action-primary-hover': semanticColor('action-primary-bg-hover'),
      danger: semanticColor('action-danger-fg'),
      'danger-subtle': semanticColor('action-danger-bg-subtle'),

      published: semanticColor('status-published'),
      empty: semanticColor('status-empty'),
      carried: semanticColor('status-carried'),
      info: semanticColor('status-info'),
    },

    // ── 타이포: §4.2. 12·13px 토큰은 존재하지 않는다 ──────────────────────
    fontSize: {
      display: typeScale('display'),
      'title-lg': typeScale('title-lg'),
      'title-md': typeScale('title-md'),
      'title-sm': typeScale('title-sm'),
      'body-lg': typeScale('body-lg'),
      'body-md': typeScale('body-md'),
      'body-sm': typeScale('body-sm'),
      caption: typeScale('caption'),
      label: typeScale('label'),
      'mono-num': typeScale('mono-num'),
    },

    // ── 간격: §5.1. 7·9·11은 정의하지 않는다 ─────────────────────────────
    spacing: {
      0: '0px',
      px: '1px',
      1: 'var(--gk-space-1)',
      2: 'var(--gk-space-2)',
      3: 'var(--gk-space-3)',
      4: 'var(--gk-space-4)',
      5: 'var(--gk-space-5)',
      6: 'var(--gk-space-6)',
      8: 'var(--gk-space-8)',
      10: 'var(--gk-space-10)',
      12: 'var(--gk-space-12)',
      16: 'var(--gk-space-16)',
      // 히트 영역·컨트롤 높이 (§5 DS-4)
      touch: '48px',
      'control-sm': '40px',
      'control-md': '48px',
      'control-lg': '56px',
      full: '100%',
    },

    screens: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
    },

    extend: {
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', '-apple-system', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        gallery: '560px',
        reading: '480px',
        studio: '1120px',
        form: '400px',
        preview: '390px',
      },
      borderRadius: {
        none: '0px',
        sm: 'var(--gk-radius-sm)',
        md: 'var(--gk-radius-md)',
        lg: 'var(--gk-radius-lg)',
        full: 'var(--gk-radius-full)',
      },
      boxShadow: {
        none: 'none',
        sheet: 'var(--gk-shadow-sheet)',
        dialog: 'var(--gk-shadow-dialog)',
      },
      zIndex: {
        base: '0',
        sticky: '10',
        overlay: '100',
        sheet: '110',
        dialog: '120',
        immersive: '200',
        toast: '300',
      },
      transitionDuration: {
        instant: 'var(--gk-duration-instant)',
        fast: 'var(--gk-duration-fast)',
        base: 'var(--gk-duration-base)',
        slow: 'var(--gk-duration-slow)',
      },
      transitionTimingFunction: {
        standard: 'var(--gk-ease-standard)',
        decelerate: 'var(--gk-ease-decelerate)',
        accelerate: 'var(--gk-ease-accelerate)',
      },
      keyframes: {
        'gk-fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'gk-sheet-in': { from: { transform: 'translateY(100%)' }, to: { transform: 'translateY(0)' } },
        'gk-dialog-in': {
          from: { opacity: '0', transform: 'scale(.98)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'gk-shimmer': { from: { backgroundPosition: '200% 0' }, to: { backgroundPosition: '-200% 0' } },
        'gk-spin': { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        'fade-in': 'gk-fade-in var(--gk-duration-fast) var(--gk-ease-decelerate)',
        'sheet-in': 'gk-sheet-in var(--gk-duration-base) var(--gk-ease-decelerate)',
        'dialog-in': 'gk-dialog-in var(--gk-duration-base) var(--gk-ease-decelerate)',
        shimmer: 'gk-shimmer 1.4s linear infinite',
        spin: 'gk-spin 1.1s linear infinite',
      },
    },
  },
  plugins: [forms({ strategy: 'base' })],
}

import { cn } from '@/shared/lib/cn'

/**
 * 아이콘 — 디자인 시스템 문서 §7
 * `/icons.svg` 스프라이트를 참조한다. 장식용은 `aria-hidden`,
 * 단독 사용 시 `label`을 반드시 넘긴다.
 */

export const ICON_NAMES = [
  'back',
  'close',
  'chevron-left',
  'chevron-right',
  'chevron-up',
  'chevron-down',
  'plus',
  'image',
  'check',
  'alert',
  'info',
  'settings',
  'bell',
  'bell-off',
  'trash',
  'eye',
  'eye-off',
  'zoom-in',
  'drag',
  'search',
  'upload',
  'spinner',
  'more',
  'arrow-up',
  'calendar',
  'refresh',
] as const

export type IconName = (typeof ICON_NAMES)[number]

const SIZE_CLASS = {
  sm: 'h-5 w-5', // 20px 기본
  md: 'h-6 w-6', // 24px 단독 버튼
  lg: 'h-icon-lg w-icon-lg', // 28px 전체화면 뷰어
} as const

export type IconProps = {
  ref?: React.Ref<SVGSVGElement>
  name: IconName
  size?: keyof typeof SIZE_CLASS
  /** 단독으로 의미를 전달할 때만 넘긴다. 없으면 장식으로 간주해 숨긴다. */
  label?: string
  className?: string
}

export function Icon({ name, size = 'sm', label, className, ref }: IconProps) {
  return (
    <svg
      ref={ref}
      className={cn(SIZE_CLASS[size], 'shrink-0', className)}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      <use href={`/icons.svg#i-${name}`} />
    </svg>
  )
}

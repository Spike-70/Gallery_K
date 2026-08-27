import type { VariantProps } from 'class-variance-authority'
import { Link, type LinkProps } from 'react-router-dom'

import { cn } from '@/shared/lib/cn'
import { buttonVariants } from '@/shared/ui/Button'

/**
 * 버튼처럼 보이는 링크 — 디자인 시스템 문서 §8.4의 다형성 요구를 채운다.
 * 이동은 `<a>`여야 한다(새 탭 열기·복사가 동작해야 하므로). 버튼 안에 링크를 넣지 않는다.
 */
export type LinkButtonProps = LinkProps & VariantProps<typeof buttonVariants>

export function LinkButton({ className, variant, size, block, ...props }: LinkButtonProps) {
  return <Link className={cn(buttonVariants({ variant, size, block }), className)} {...props} />
}

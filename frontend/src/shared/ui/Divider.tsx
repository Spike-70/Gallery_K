import { cn } from '@/shared/lib/cn'

/** Divider — 1px hairline. 여백으로 충분하면 쓰지 않는다(§8.1). */
export function Divider({
  className,
  ref,
}: {
  className?: string
  ref?: React.Ref<HTMLHRElement>
}) {
  return <hr ref={ref} className={cn('border-0 border-t border-border-default', className)} />
}

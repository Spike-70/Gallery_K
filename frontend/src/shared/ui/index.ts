/**
 * 디자인 시스템 프리미티브 공개 표면 — 디자인 시스템 문서 §8.1
 *
 * 이 계층은 **도메인 타입을 프롭으로 받지 않는다**(프런트 §4.3).
 * 이 경계가 흐려지면 디자인 시스템이 제품에 종속되어 재사용이 불가능해진다.
 */

export { BackLink, BackLinkGroup, TopBackSlot } from '@/shared/ui/BackLink'
export { Badge } from '@/shared/ui/Badge'
export { Banner } from '@/shared/ui/Banner'
export { BottomSheet } from '@/shared/ui/BottomSheet'
export { Button, buttonVariants } from '@/shared/ui/Button'
export { LinkButton } from '@/shared/ui/LinkButton'
export { CharCounter } from '@/shared/ui/CharCounter'
export { Checkbox } from '@/shared/ui/Checkbox'
export { DateField } from '@/shared/ui/DateField'
export { AlertDialog, Dialog } from '@/shared/ui/Dialog'
export { Divider } from '@/shared/ui/Divider'
export { EmptyState } from '@/shared/ui/EmptyState'
export { ErrorState } from '@/shared/ui/ErrorState'
export { FieldGroup, fieldIds } from '@/shared/ui/FieldGroup'
export { FilterChip } from '@/shared/ui/FilterChip'
export { Icon, ICON_NAMES, type IconName } from '@/shared/ui/Icon'
export { IconButton } from '@/shared/ui/IconButton'
export { Menu, type MenuItem } from '@/shared/ui/Menu'
export { ProgressRing } from '@/shared/ui/ProgressRing'
export { PullToRefresh } from '@/shared/ui/PullToRefresh'
export { ScreenSkeleton, Skeleton } from '@/shared/ui/Skeleton'
export { Spinner } from '@/shared/ui/Spinner'
export { StatusChip } from '@/shared/ui/StatusChip'
export { Switch } from '@/shared/ui/Switch'
export { TextArea } from '@/shared/ui/TextArea'
export { TextField } from '@/shared/ui/TextField'
export { TextButton, TextLink } from '@/shared/ui/TextLink'
export { TimeSelectSheet } from '@/shared/ui/TimeSelectSheet'
export { ToastViewport } from '@/shared/ui/Toast'
export { toast, useToastStore } from '@/shared/ui/toastStore'

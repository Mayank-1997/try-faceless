import { Avatar } from '../primitives/Avatar'
import { Badge } from '../primitives/Badge'
import { cn } from '../lib/cn'
import { initials } from '@ai-video-studio/shared-utils'

export interface UserCardProps {
  name: string
  email: string
  role?: string
  avatarUrl?: string
  status?: 'active' | 'inactive' | 'suspended' | 'pending'
  onClick?: () => void
  className?: string
}

const statusVariant = {
  active: 'success' as const,
  inactive: 'secondary' as const,
  suspended: 'error' as const,
  pending: 'warning' as const,
}

export function UserCard({
  name,
  email,
  role,
  avatarUrl,
  status = 'active',
  onClick,
  className,
}: UserCardProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] p-4',
        onClick && 'cursor-pointer transition-shadow hover:shadow-[var(--shadow-sm)]',
        className
      )}
      onClick={onClick}
    >
      <Avatar src={avatarUrl} fallback={initials(name)} size="md" />
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-[var(--fg-default)]">{name}</p>
        <p className="truncate text-xs text-[var(--fg-muted)]">{email}</p>
      </div>
      <div className="flex flex-col items-end gap-1">
        {role && <Badge variant="secondary">{role}</Badge>}
        <Badge variant={statusVariant[status]}>{status}</Badge>
      </div>
    </div>
  )
}

import { Card, CardContent, CardHeader, CardTitle } from '../primitives/Card'
import { Badge } from '../primitives/Badge'
import { Progress } from '../primitives/Progress'
import { Video, Clock, CheckCircle, XCircle, Loader2 } from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import { cn } from '../lib/cn'

export interface ProjectCardProps {
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress?: number
  thumbnailUrl?: string
  createdAt: string
  updatedAt: string
  onClick?: () => void
  className?: string
}

const statusConfig = {
  pending: { label: 'Pending', variant: 'secondary' as const, icon: Clock },
  running: { label: 'Running', variant: 'info' as const, icon: Loader2 },
  completed: { label: 'Completed', variant: 'success' as const, icon: CheckCircle },
  failed: { label: 'Failed', variant: 'error' as const, icon: XCircle },
  cancelled: { label: 'Cancelled', variant: 'secondary' as const, icon: XCircle },
}

export function ProjectCard({
  title,
  status,
  progress = 0,
  thumbnailUrl,
  createdAt,
  updatedAt,
  onClick,
  className,
}: ProjectCardProps) {
  const config = statusConfig[status]
  const StatusIcon = config.icon

  return (
    <Card
      className={cn('cursor-pointer transition-shadow hover:shadow-[var(--shadow-md)]', className)}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="line-clamp-1 text-base">{title}</CardTitle>
          <Badge variant={config.variant}>
            <StatusIcon className={cn('mr-1 h-3 w-3', status === 'running' && 'animate-spin')} />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 aspect-video w-full overflow-hidden rounded-md bg-[var(--bg-surface)]">
          {thumbnailUrl ? (
            <img src={thumbnailUrl} alt={title} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center">
              <Video className="h-8 w-8 text-[var(--fg-subtle)]" />
            </div>
          )}
        </div>
        {status === 'running' && (
          <Progress value={progress} className="mb-2" />
        )}
        <div className="flex items-center justify-between text-xs text-[var(--fg-muted)]">
          <span>Created {formatRelativeTime(createdAt)}</span>
          <span>Updated {formatRelativeTime(updatedAt)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

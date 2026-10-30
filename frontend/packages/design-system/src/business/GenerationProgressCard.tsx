import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../primitives/Card'
import { Badge } from '../primitives/Badge'
import { Progress } from '../primitives/Progress'
import { cn } from '../lib/cn'

export interface GenerationProgressCardProps {
  title: string
  step: string
  progress: number
  steps?: Array<{ label: string; status: 'pending' | 'running' | 'completed' | 'failed' }>
  className?: string
}

export function GenerationProgressCard({
  title,
  step,
  progress,
  steps = [],
  className,
}: GenerationProgressCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{step}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={progress} />
        {steps.length > 0 && (
          <div className="space-y-2">
            {steps.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <div
                  className={cn(
                    'h-2 w-2 rounded-full',
                    s.status === 'completed' && 'bg-[var(--success)]',
                    s.status === 'running' && 'bg-[var(--brand-default)]',
                    s.status === 'failed' && 'bg-[var(--error)]',
                    s.status === 'pending' && 'bg-[var(--fg-subtle)]'
                  )}
                />
                <span
                  className={cn(
                    s.status === 'pending' && 'text-[var(--fg-muted)]',
                    s.status === 'completed' && 'text-[var(--fg-default)]',
                    s.status === 'running' && 'font-medium text-[var(--fg-default)]',
                    s.status === 'failed' && 'text-[var(--error)]'
                  )}
                >
                  {s.label}
                </span>
                {s.status === 'running' && <Badge variant="info">In Progress</Badge>}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

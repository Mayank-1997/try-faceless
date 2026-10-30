import { Card, CardContent, CardHeader, CardTitle } from '../primitives/Card'
import { Badge } from '../primitives/Badge'
import { Key, MoreVertical, Copy } from '@ai-video-studio/icons'
import { formatRelativeTime, maskApiKey } from '@ai-video-studio/shared-utils'
import { cn } from '../lib/cn'

export interface ApiKeyCardProps {
  name: string
  keyPrefix: string
  status: 'active' | 'revoked' | 'expired'
  scopes: string[]
  expiresAt: string | null
  lastUsedAt: string | null
  createdAt: string
  onCopy?: () => void
  onRevoke?: () => void
  className?: string
}

const statusVariant = {
  active: 'success' as const,
  revoked: 'error' as const,
  expired: 'warning' as const,
}

export function ApiKeyCard({
  name,
  keyPrefix,
  status,
  scopes,
  expiresAt,
  lastUsedAt,
  createdAt,
  onCopy,
  onRevoke,
  className,
}: ApiKeyCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-[var(--fg-muted)]" />
            <CardTitle className="text-base">{name}</CardTitle>
          </div>
          <Badge variant={statusVariant[status]}>{status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2">
          <code className="rounded bg-[var(--bg-surface)] px-2 py-1 text-xs text-[var(--fg-muted)]">
            {maskApiKey(keyPrefix + '••••••••')}
          </code>
          {onCopy && (
            <button
              onClick={onCopy}
              className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]"
              aria-label="Copy API key"
            >
              <Copy className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {scopes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {scopes.map((scope) => (
              <Badge key={scope} variant="outline">
                {scope}
              </Badge>
            ))}
          </div>
        )}
        <div className="space-y-1 text-xs text-[var(--fg-muted)]">
          <p>Created {formatRelativeTime(createdAt)}</p>
          {lastUsedAt && <p>Last used {formatRelativeTime(lastUsedAt)}</p>}
          {expiresAt && <p>Expires {formatRelativeTime(expiresAt)}</p>}
        </div>
        {onRevoke && status === 'active' && (
          <button
            onClick={onRevoke}
            className="text-xs text-[var(--error)] hover:underline"
          >
            Revoke
          </button>
        )}
      </CardContent>
    </Card>
  )
}

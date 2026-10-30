'use client'

import Link from 'next/link'
import { useState } from 'react'
import {
  usePlatformOverview,
  useSystemHealth,
  useAuditLogs,
  useFeatureFlags,
  useCreateFeatureFlag,
  useUpdateFeatureFlag,
  useDeleteFeatureFlag,
  useOrganizations,
} from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Badge,
  Skeleton,
  Input,
  Label,
  Select,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  Shield,
  Activity,
  Server,
  Database,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Flag,
  Building2,
  Users,
  Terminal,
  Plus,
  Trash2,
  RefreshCw,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { FeatureFlagDTO, AuditEntryDTO } from '@ai-video-studio/shared-types'

const healthStatusConfig: Record<string, { variant: 'success' | 'warning' | 'error' | 'secondary'; icon: typeof CheckCircle2 }> = {
  healthy: { variant: 'success', icon: CheckCircle2 },
  degraded: { variant: 'warning', icon: AlertTriangle },
  unhealthy: { variant: 'error', icon: XCircle },
  unknown: { variant: 'secondary', icon: Activity },
}

export default function AdminPage() {
  const { addToast } = useToast()
  const [showFlagForm, setShowFlagForm] = useState(false)
  const [flagKey, setFlagKey] = useState('')
  const [flagName, setFlagName] = useState('')
  const [flagScope, setFlagScope] = useState('global')

  const { data: overview, isLoading: overviewLoading } = usePlatformOverview()
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: auditLogs, isLoading: logsLoading } = useAuditLogs(50)
  const { data: flags, isLoading: flagsLoading } = useFeatureFlags()
  const { data: orgs, isLoading: orgsLoading } = useOrganizations()

  const createFlag = useCreateFeatureFlag()
  const updateFlag = useUpdateFeatureFlag()
  const deleteFlag = useDeleteFeatureFlag()

  const handleCreateFlag = () => {
    if (!flagKey.trim() || !flagName.trim()) {
      addToast({ title: 'Key and name are required', variant: 'error' })
      return
    }
    createFlag.mutate(
      { key: flagKey, name: flagName, scope: flagScope, enabled: true },
      {
        onSuccess: () => {
          addToast({ title: 'Feature flag created', variant: 'success' })
          setShowFlagForm(false)
          setFlagKey('')
          setFlagName('')
        },
      }
    )
  }

  const handleToggleFlag = (flag: FeatureFlagDTO) => {
    updateFlag.mutate(
      { key: flag.key, body: { enabled: !flag.enabled } },
      {
        onSuccess: () => addToast({ title: `Flag ${!flag.enabled ? 'enabled' : 'disabled'}`, variant: 'success' }),
      }
    )
  }

  const handleDeleteFlag = (key: string) => {
    deleteFlag.mutate(key, {
      onSuccess: () => addToast({ title: 'Feature flag deleted', variant: 'info' }),
    })
  }

  if (overviewLoading || healthLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const healthConfig = healthStatusConfig[health?.overall_status ?? 'unknown'] ?? healthStatusConfig.unknown
  const HealthIcon = healthConfig.icon

  const overviewStats = [
    {
      label: 'Total Projects',
      value: overview?.analytics?.total_projects ?? 0,
      icon: Activity,
      color: 'text-[var(--brand-default)]',
    },
    {
      label: 'Health',
      value: health?.overall_status ?? 'unknown',
      icon: HealthIcon,
      color: `text-[var(--status-${healthConfig.variant === 'success' ? 'success' : healthConfig.variant === 'warning' ? 'warning' : healthConfig.variant === 'error' ? 'error' : 'info'})]`,
    },
    {
      label: 'Invoices',
      value: overview?.billing?.total_invoices ?? 0,
      icon: Server,
      color: 'text-[var(--fg-muted)]',
    },
    {
      label: 'Organizations',
      value: orgs?.length ?? 0,
      icon: Building2,
      color: 'text-[var(--fg-muted)]',
    },
  ]

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-bold text-[var(--fg-default)]">Admin</h1>
          <p className="text-sm text-[var(--fg-muted)]">Platform administration and monitoring</p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-4">
        {overviewStats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs text-[var(--fg-muted)]">{stat.label}</p>
                <p className="text-xl font-bold capitalize text-[var(--fg-default)]">{stat.value}</p>
              </div>
              <stat.icon className={`h-7 w-7 ${stat.color}`} />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System health */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>System Health</CardTitle>
          </div>
          <CardDescription>Component health checks (auto-refreshing every 30s)</CardDescription>
        </CardHeader>
        <CardContent>
          {health && health.checks.length > 0 ? (
            <div className="space-y-2">
              {health.checks.map((check) => {
                const config = healthStatusConfig[check.status] ?? healthStatusConfig.unknown
                const CheckIcon = config.icon
                return (
                  <div
                    key={check.component}
                    className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-3"
                  >
                    <CheckIcon className={`h-4 w-4 shrink-0 text-[var(--status-${config.variant === 'success' ? 'success' : config.variant === 'warning' ? 'warning' : config.variant === 'error' ? 'error' : 'info'})]`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-[var(--fg-default)]">{check.component}</span>
                      <p className="text-xs text-[var(--fg-muted)]">{check.message}</p>
                    </div>
                    <Badge variant={config.variant}>{check.status}</Badge>
                    <span className="text-xs text-[var(--fg-muted)]">{check.latency_ms.toFixed(0)}ms</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-[var(--fg-muted)]">
              <Activity className="h-4 w-4" />
              No health checks available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feature flags */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flag className="h-5 w-5 text-[var(--fg-muted)]" />
              <CardTitle>Feature Flags</CardTitle>
            </div>
            <Button size="sm" onClick={() => setShowFlagForm(!showFlagForm)}>
              <Plus className="mr-1 h-3 w-3" />
              New Flag
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {showFlagForm && (
            <div className="mb-4 grid gap-3 rounded-lg border border-[var(--border-default)] p-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="flag-key">Key</Label>
                <Input id="flag-key" value={flagKey} onChange={(e) => setFlagKey(e.target.value)} placeholder="my_feature" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="flag-name">Name</Label>
                <Input id="flag-name" value={flagName} onChange={(e) => setFlagName(e.target.value)} placeholder="My Feature" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="flag-scope">Scope</Label>
                <Select id="flag-scope" value={flagScope} onChange={(e) => setFlagScope(e.target.value)}>
                  <option value="global">Global</option>
                  <option value="user">User</option>
                  <option value="organization">Organization</option>
                  <option value="plan">Plan</option>
                </Select>
              </div>
              <div className="md:col-span-3">
                <Button size="sm" onClick={handleCreateFlag} disabled={createFlag.isPending}>
                  Create Flag
                </Button>
              </div>
            </div>
          )}

          {flagsLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : flags && flags.length > 0 ? (
            <div className="space-y-2">
              {flags.map((flag: FeatureFlagDTO) => (
                <div
                  key={flag.key}
                  className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--fg-default)]">{flag.name}</span>
                      <Badge variant="outline" className="text-xs">{flag.key}</Badge>
                      <Badge variant="secondary" className="capitalize">{flag.scope}</Badge>
                    </div>
                    {flag.description && (
                      <p className="text-xs text-[var(--fg-muted)]">{flag.description}</p>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleFlag(flag)}
                    disabled={updateFlag.isPending}
                  >
                    {flag.enabled ? 'Disable' : 'Enable'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteFlag(flag.key)}
                    disabled={deleteFlag.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-[var(--fg-error)]" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--fg-muted)]">No feature flags configured.</p>
          )}
        </CardContent>
      </Card>

      {/* Organizations */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Organizations</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {orgsLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : orgs && orgs.length > 0 ? (
            <div className="space-y-2">
              {orgs.map((org) => (
                <div
                  key={org.id}
                  className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-3"
                >
                  <Building2 className="h-4 w-4 shrink-0 text-[var(--fg-muted)]" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-[var(--fg-default)]">{org.name}</span>
                    <p className="text-xs text-[var(--fg-muted)]">{org.slug}</p>
                  </div>
                  <Badge variant="secondary">
                    <Users className="mr-1 h-3 w-3" />
                    {org.member_count}/{org.max_members}
                  </Badge>
                  <Badge variant="outline" className="capitalize">{org.plan_type}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--fg-muted)]">No organizations.</p>
          )}
        </CardContent>
      </Card>

      {/* Audit logs */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Audit Logs</CardTitle>
          </div>
          <CardDescription>Recent platform activity</CardDescription>
        </CardHeader>
        <CardContent>
          {logsLoading ? (
            <Skeleton className="h-48 w-full" />
          ) : auditLogs && auditLogs.length > 0 ? (
            <div className="space-y-1">
              {auditLogs.map((entry: AuditEntryDTO) => (
                <div
                  key={entry.id}
                  className="flex items-center gap-3 rounded-md border border-[var(--border-default)] px-3 py-2 text-xs"
                >
                  <Badge variant="outline" className="shrink-0 capitalize">{entry.action}</Badge>
                  <span className="text-[var(--fg-muted)]">{entry.user_id}</span>
                  <span className="text-[var(--fg-default)]">{entry.resource_type}</span>
                  <span className="ml-auto text-[var(--fg-muted)]">
                    {formatRelativeTime(entry.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--fg-muted)]">No audit logs.</p>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href="/settings">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to settings
          </Button>
        </Link>
        <Link href="/analytics">
          <Button variant="outline">Go to analytics</Button>
        </Link>
      </div>
    </div>
  )
}

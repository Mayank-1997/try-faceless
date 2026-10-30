'use client'

import Link from 'next/link'
import { useAuthStore } from '@ai-video-studio/platform-kernel'
import {
  useAnalyticsSummary,
  useCostBreakdown,
  useUsageSummary,
} from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Skeleton,
  Badge,
  Button,
} from '@ai-video-studio/design-system'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowLeft,
  Cpu,
  Image,
  Video,
  Mic,
  Film,
  UploadCloud,
  Zap,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'

export default function AnalyticsPage() {
  const user = useAuthStore((s) => s.user)
  const userId = user?.id ?? ''

  const { data: analytics, isLoading: analyticsLoading } = useAnalyticsSummary()
  const { data: costs, isLoading: costsLoading } = useCostBreakdown()
  const { data: usage, isLoading: usageLoading } = useUsageSummary(userId)

  if (analyticsLoading || costsLoading || usageLoading) {
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

  const stats = [
    {
      label: 'Total Projects',
      value: analytics?.total_projects ?? 0,
      icon: BarChart3,
      color: 'text-[var(--brand-default)]',
    },
    {
      label: 'Success Rate',
      value: `${(analytics?.success_rate ?? 0).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-[var(--status-success)]',
    },
    {
      label: 'Avg Gen Time',
      value: `${(analytics?.avg_generation_time ?? 0).toFixed(1)}s`,
      icon: Clock,
      color: 'text-[var(--status-warning)]',
    },
    {
      label: 'Total Cost',
      value: `$${(costs?.total_cost ?? 0).toFixed(2)}`,
      icon: DollarSign,
      color: 'text-[var(--status-error)]',
    },
  ]

  const usageStats = [
    { label: 'Images', value: usage?.images_generated ?? 0, icon: Image, unit: '' },
    { label: 'Videos', value: usage?.videos_generated ?? 0, icon: Video, unit: '' },
    { label: 'Voice', value: (usage?.voice_minutes ?? 0).toFixed(1), icon: Mic, unit: 'min' },
    { label: 'Rendering', value: (usage?.rendering_minutes ?? 0).toFixed(1), icon: Film, unit: 'min' },
    { label: 'Publishing', value: usage?.publishing_count ?? 0, icon: UploadCloud, unit: '' },
    { label: 'Tokens', value: usage?.token_usage ?? 0, icon: Zap, unit: '' },
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
          <h1 className="text-xl font-bold text-[var(--fg-default)]">Analytics</h1>
          <p className="text-sm text-[var(--fg-muted)]">Usage, costs, and performance metrics</p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs text-[var(--fg-muted)]">{stat.label}</p>
                <p className="text-2xl font-bold text-[var(--fg-default)]">{stat.value}</p>
              </div>
              <stat.icon className={`h-8 w-8 ${stat.color}`} />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Project analytics */}
      <Card>
        <CardHeader>
          <CardTitle>Project Analytics</CardTitle>
          <CardDescription>Success rates and timing across all projects</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[var(--status-success)]" />
                <span className="text-sm font-medium text-[var(--fg-default)]">Successful</span>
              </div>
              <p className="mt-2 text-2xl font-bold text-[var(--fg-default)]">
                {analytics?.successful_projects ?? 0}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-[var(--status-error)]" />
                <span className="text-sm font-medium text-[var(--fg-default)]">Failed</span>
              </div>
              <p className="mt-2 text-2xl font-bold text-[var(--fg-default)]">
                {analytics?.failed_projects ?? 0}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-[var(--fg-muted)]" />
                <span className="text-sm font-medium text-[var(--fg-default)]">Failure Rate</span>
              </div>
              <p className="mt-2 text-2xl font-bold text-[var(--fg-default)]">
                {(analytics?.failure_rate ?? 0).toFixed(1)}%
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="text-sm">
              <span className="text-[var(--fg-muted)]">Avg Generation Time</span>
              <p className="font-medium text-[var(--fg-default)]">
                {(analytics?.avg_generation_time ?? 0).toFixed(1)}s
              </p>
            </div>
            <div className="text-sm">
              <span className="text-[var(--fg-muted)]">Avg Rendering Time</span>
              <p className="font-medium text-[var(--fg-default)]">
                {(analytics?.avg_rendering_time ?? 0).toFixed(1)}s
              </p>
            </div>
            <div className="text-sm">
              <span className="text-[var(--fg-muted)]">Avg Publishing Time</span>
              <p className="font-medium text-[var(--fg-default)]">
                {(analytics?.avg_publishing_time ?? 0).toFixed(1)}s
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Usage breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Resource Usage</CardTitle>
          <CardDescription>Your resource consumption this period</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
            {usageStats.map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-[var(--border-default)] p-3 text-center"
              >
                <item.icon className="mx-auto h-6 w-6 text-[var(--fg-muted)]" />
                <p className="mt-2 text-xs text-[var(--fg-muted)]">{item.label}</p>
                <p className="text-lg font-bold text-[var(--fg-default)]">
                  {item.value}
                  {item.unit && (
                    <span className="text-xs text-[var(--fg-muted)]"> {item.unit}</span>
                  )}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Provider usage */}
      {usage && Object.keys(usage.provider_usage).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Provider Usage</CardTitle>
            <CardDescription>API calls by provider</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(usage.provider_usage).map(([provider, count]) => (
                <div
                  key={provider}
                  className="flex items-center justify-between rounded-lg border border-[var(--border-default)] p-3"
                >
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-[var(--fg-muted)]" />
                    <span className="text-sm font-medium text-[var(--fg-default)] capitalize">
                      {provider}
                    </span>
                  </div>
                  <Badge variant="secondary">{count} calls</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cost breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Cost Analytics</CardTitle>
          <CardDescription>Cost breakdown across dimensions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <span className="text-xs text-[var(--fg-muted)]">Total Cost</span>
              <p className="text-2xl font-bold text-[var(--fg-default)]">
                ${(costs?.total_cost ?? 0).toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <span className="text-xs text-[var(--fg-muted)]">Revenue</span>
              <p className="text-2xl font-bold text-[var(--fg-default)]">
                ${(costs?.revenue ?? 0).toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--border-default)] p-4">
              <span className="text-xs text-[var(--fg-muted)]">Profit Margin</span>
              <p className="text-2xl font-bold text-[var(--fg-default)]">
                {(costs?.profit_margin ?? 0).toFixed(1)}%
              </p>
            </div>
          </div>

          {costs && Object.keys(costs.cost_per_provider).length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-[var(--fg-default)]">Cost by Provider</h4>
              <div className="space-y-2">
                {Object.entries(costs.cost_per_provider).map(([provider, cost]) => (
                  <div
                    key={provider}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="capitalize text-[var(--fg-default)]">{provider}</span>
                    <span className="font-medium text-[var(--fg-default)]">${cost.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {costs && Object.keys(costs.daily_costs).length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-[var(--fg-default)]">Daily Costs (Last 7)</h4>
              <div className="space-y-1">
                {Object.entries(costs.daily_costs)
                  .slice(-7)
                  .map(([date, cost]) => (
                    <div key={date} className="flex items-center justify-between text-xs">
                      <span className="text-[var(--fg-muted)]">{formatRelativeTime(date)}</span>
                      <span className="font-medium text-[var(--fg-default)]">${cost.toFixed(2)}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Most used providers */}
      {analytics && Object.keys(analytics.most_used_providers).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Most Used Providers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(analytics.most_used_providers).map(([provider, count]) => (
                <div
                  key={provider}
                  className="flex items-center justify-between rounded-lg border border-[var(--border-default)] p-3"
                >
                  <span className="text-sm font-medium text-[var(--fg-default)] capitalize">
                    {provider}
                  </span>
                  <Badge variant="secondary">{count} projects</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href="/dashboard">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to dashboard
          </Button>
        </Link>
        <Link href="/billing">
          <Button variant="outline">Go to billing</Button>
        </Link>
      </div>
    </div>
  )
}

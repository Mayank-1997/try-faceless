'use client'

import Link from 'next/link'
import { useAuthStore } from '@ai-video-studio/platform-kernel'
import {
  usePlans,
  useSubscription,
  useCreditBalance,
  useInvoices,
  useCreateSubscription,
  useCancelSubscription,
  useChangePlan,
  useAddCredits,
  usePayInvoice,
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
  Select,
  Input,
  Label,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  CreditCard,
  DollarSign,
  Crown,
  Check,
  X,
  Zap,
  Download,
  Receipt,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { PlanDTO, InvoiceDTO } from '@ai-video-studio/shared-types'

const invoiceStatusConfig: Record<string, { variant: 'default' | 'secondary' | 'success' | 'warning' | 'error'; label: string }> = {
  draft: { variant: 'secondary', label: 'Draft' },
  pending: { variant: 'warning', label: 'Pending' },
  paid: { variant: 'success', label: 'Paid' },
  void: { variant: 'error', label: 'Void' },
}

export default function BillingPage() {
  const user = useAuthStore((s) => s.user)
  const userId = user?.id ?? ''
  const { addToast } = useToast()

  const { data: plans, isLoading: plansLoading } = usePlans()
  const { data: subscription, isLoading: subLoading } = useSubscription(userId)
  const { data: credits, isLoading: creditsLoading } = useCreditBalance(userId)
  const { data: invoices, isLoading: invoicesLoading } = useInvoices(userId)

  const createSub = useCreateSubscription()
  const cancelSub = useCancelSubscription()
  const changePlan = useChangePlan()
  const addCreditsMut = useAddCredits()
  const payInvoiceMut = usePayInvoice()

  const [selectedPlan, setSelectedPlan] = useSelectedPlanState()
  const [creditType, setCreditType] = useCreditTypeState()
  const [creditAmount, setCreditAmount] = useCreditAmountState()

  const handleSubscribe = (planId: string) => {
    createSub.mutate(
      { userId, body: { plan_id: planId } },
      {
        onSuccess: () => addToast({ title: 'Subscription created', variant: 'success' }),
        onError: () => addToast({ title: 'Failed to create subscription', variant: 'error' }),
      }
    )
  }

  const handleCancel = () => {
    cancelSub.mutate(userId, {
      onSuccess: () => addToast({ title: 'Subscription cancelled', variant: 'info' }),
    })
  }

  const handleChangePlan = (newPlanId: string) => {
    changePlan.mutate(
      { userId, planId: newPlanId },
      {
        onSuccess: () => addToast({ title: 'Plan changed', variant: 'success' }),
      }
    )
  }

  const handleAddCredits = () => {
    addCreditsMut.mutate(
      { userId, body: { credit_type: creditType, amount: Number(creditAmount) } },
      {
        onSuccess: () => {
          addToast({ title: 'Credits added', variant: 'success' })
          setCreditAmount('100')
        },
      }
    )
  }

  const handlePayInvoice = (invoiceId: string) => {
    payInvoiceMut.mutate(invoiceId, {
      onSuccess: () => addToast({ title: 'Invoice paid', variant: 'success' }),
    })
  }

  if (plansLoading || subLoading || creditsLoading || invoicesLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const currentPlanId = subscription?.plan_id ?? ''
  const allPlans = plans ?? []
  const allInvoices = invoices ?? []

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
          <h1 className="text-xl font-bold text-[var(--fg-default)]">Billing</h1>
          <p className="text-sm text-[var(--fg-muted)]">Manage your subscription, credits, and invoices</p>
        </div>
      </div>

      {/* Current subscription */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Current Subscription</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {subscription ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-[var(--fg-muted)]">Plan</span>
                  <p className="text-lg font-bold capitalize text-[var(--fg-default)]">
                    {subscription.plan_id}
                  </p>
                </div>
                <Badge variant={subscription.status === 'active' ? 'success' : 'warning'}>
                  {subscription.status}
                </Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-3 text-sm">
                <div>
                  <span className="text-[var(--fg-muted)]">Started</span>
                  <p className="font-medium text-[var(--fg-default)]">
                    {formatRelativeTime(subscription.started_at)}
                  </p>
                </div>
                <div>
                  <span className="text-[var(--fg-muted)]">Period End</span>
                  <p className="font-medium text-[var(--fg-default)]">
                    {subscription.current_period_end
                      ? formatRelativeTime(subscription.current_period_end)
                      : '—'}
                  </p>
                </div>
                {subscription.trial_end && (
                  <div>
                    <span className="text-[var(--fg-muted)]">Trial End</span>
                    <p className="font-medium text-[var(--fg-default)]">
                      {formatRelativeTime(subscription.trial_end)}
                    </p>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleCancel} disabled={cancelSub.isPending}>
                  Cancel Subscription
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-[var(--fg-muted)]">
              No active subscription. Choose a plan below to get started.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available plans */}
      <Card>
        <CardHeader>
          <CardTitle>Available Plans</CardTitle>
          <CardDescription>Choose the plan that fits your needs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {allPlans.map((plan: PlanDTO) => {
              const isCurrent = plan.id === currentPlanId
              return (
                <div
                  key={plan.id}
                  className={`rounded-lg border-2 p-4 ${
                    isCurrent
                      ? 'border-[var(--brand-default)]'
                      : 'border-[var(--border-default)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-[var(--fg-default)]">{plan.name}</h3>
                    {isCurrent && <Badge variant="success">Current</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-[var(--fg-muted)]">{plan.description}</p>
                  <div className="mt-3">
                    <span className="text-2xl font-bold text-[var(--fg-default)]">
                      ${plan.price_monthly}
                    </span>
                    <span className="text-sm text-[var(--fg-muted)]">/month</span>
                  </div>
                  <div className="mt-3 space-y-1 text-xs">
                    <PlanFeature label={`${plan.features.max_projects} projects`} included />
                    <PlanFeature label={`${plan.features.max_images_per_month} images/mo`} included />
                    <PlanFeature label={`${plan.features.max_videos_per_month} videos/mo`} included />
                    <PlanFeature label={`${plan.features.max_voice_minutes_per_month} voice min`} included />
                    <PlanFeature label={`${plan.features.max_rendering_minutes_per_month} render min`} included />
                    <PlanFeature label={`${plan.features.max_storage_gb} GB storage`} included />
                    <PlanFeature label="Custom branding" included={plan.features.custom_branding} />
                    <PlanFeature label="Priority support" included={plan.features.priority_support} />
                    <PlanFeature label="API access" included={plan.features.api_access} />
                    <PlanFeature label="Advanced analytics" included={plan.features.advanced_analytics} />
                  </div>
                  <div className="mt-4">
                    {isCurrent ? (
                      <Button variant="outline" size="sm" disabled>
                        Current Plan
                      </Button>
                    ) : subscription ? (
                      <Button
                        size="sm"
                        onClick={() => handleChangePlan(plan.id)}
                        disabled={changePlan.isPending}
                      >
                        Switch to {plan.name}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleSubscribe(plan.id)}
                        disabled={createSub.isPending}
                      >
                        Subscribe
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Credits */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Credits</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {credits && Object.keys(credits.credits).length > 0 ? (
              <div className="grid gap-3 md:grid-cols-3">
                {Object.entries(credits.credits).map(([type, amount]) => (
                  <div
                    key={type}
                    className="rounded-lg border border-[var(--border-default)] p-3"
                  >
                    <span className="text-xs capitalize text-[var(--fg-muted)]">{type}</span>
                    <p className="text-xl font-bold text-[var(--fg-default)]">{amount.toFixed(0)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--fg-muted)]">No credits balance.</p>
            )}

            <div className="flex items-end gap-3">
              <div className="space-y-1">
                <Label htmlFor="credit-type">Type</Label>
                <Select
                  id="credit-type"
                  value={creditType}
                  onChange={(e) => setCreditType(e.target.value)}
                  className="w-32"
                >
                  <option value="image">Image</option>
                  <option value="video">Video</option>
                  <option value="voice">Voice</option>
                  <option value="render">Render</option>
                  <option value="publish">Publish</option>
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="credit-amount">Amount</Label>
                <Input
                  id="credit-amount"
                  type="number"
                  value={creditAmount}
                  onChange={(e) => setCreditAmount(e.target.value)}
                  className="w-24"
                />
              </div>
              <Button onClick={handleAddCredits} disabled={addCreditsMut.isPending}>
                Add Credits
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoices */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Receipt className="h-5 w-5 text-[var(--fg-muted)]" />
            <CardTitle>Invoices</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {allInvoices.length > 0 ? (
            <div className="space-y-2">
              {allInvoices.map((inv: InvoiceDTO) => {
                const config = invoiceStatusConfig[inv.status] ?? invoiceStatusConfig.pending
                return (
                  <div
                    key={inv.id}
                    className="flex items-center gap-4 rounded-lg border border-[var(--border-default)] p-3"
                  >
                    <CreditCard className="h-5 w-5 shrink-0 text-[var(--fg-muted)]" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--fg-default)]">
                          {inv.id.slice(0, 8)}...
                        </span>
                        <Badge variant={config.variant}>{config.label}</Badge>
                      </div>
                      <div className="text-xs text-[var(--fg-muted)]">
                        {formatRelativeTime(inv.issued_at)} · {inv.items.length} item(s)
                      </div>
                    </div>
                    <span className="text-sm font-bold text-[var(--fg-default)]">
                      ${inv.total.toFixed(2)}
                    </span>
                    {inv.status === 'pending' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePayInvoice(inv.id)}
                        disabled={payInvoiceMut.isPending}
                      >
                        Pay Now
                      </Button>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-[var(--fg-muted)]">No invoices yet.</p>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href="/analytics">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to analytics
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="outline">Go to settings</Button>
        </Link>
      </div>
    </div>
  )
}

function PlanFeature({ label, included }: { label: string; included: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {included ? (
        <Check className="h-3 w-3 text-[var(--status-success)]" />
      ) : (
        <X className="h-3 w-3 text-[var(--fg-muted)]" />
      )}
      <span className={included ? 'text-[var(--fg-default)]' : 'text-[var(--fg-muted)]'}>
        {label}
      </span>
    </div>
  )
}

// Simple state hooks (inline to avoid extra files)
import { useState } from 'react'

function useSelectedPlanState() {
  return useState('')
}
function useCreditTypeState() {
  return useState('image')
}
function useCreditAmountState() {
  return useState('100')
}

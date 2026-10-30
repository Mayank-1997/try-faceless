import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type { ApiError } from '@ai-video-studio/shared-types'
import type {
  AnalyticsSummaryDTO,
  CostBreakdownDTO,
  UsageSummaryDTO,
  PlanDTO,
  SubscriptionDTO,
  CreditBalanceDTO,
  InvoiceDTO,
  OrganizationDTO,
  TeamMemberDTO,
  FeatureFlagDTO,
  PlatformOverviewDTO,
  HealthReportDTO,
  AuditEntryDTO,
  CreateSubscriptionRequest,
  AddCreditsRequest,
  CreateOrganizationRequest,
  CreateFeatureFlagRequest,
  MessageResponse,
} from '@ai-video-studio/shared-types'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const platformKeys = {
  all: ['platform'] as const,
  analytics: () => [...platformKeys.all, 'analytics'] as const,
  analyticsSummary: (params?: Record<string, unknown>) =>
    [...platformKeys.analytics(), 'summary', params] as const,
  costBreakdown: (params?: Record<string, unknown>) =>
    [...platformKeys.analytics(), 'costs', params] as const,
  usage: (userId: string) => [...platformKeys.all, 'usage', userId] as const,
  plans: () => [...platformKeys.all, 'plans'] as const,
  plan: (planId: string) => [...platformKeys.all, 'plans', planId] as const,
  subscription: (userId: string) => [...platformKeys.all, 'subscription', userId] as const,
  credits: (userId: string) => [...platformKeys.all, 'credits', userId] as const,
  invoices: (userId?: string) => [...platformKeys.all, 'invoices', userId] as const,
  organizations: (userId?: string) => [...platformKeys.all, 'organizations', userId] as const,
  organization: (orgId: string) => [...platformKeys.all, 'organizations', orgId] as const,
  members: (orgId: string) => [...platformKeys.all, 'organizations', orgId, 'members'] as const,
  featureFlags: (scope?: string) => [...platformKeys.all, 'feature-flags', scope] as const,
  featureFlag: (key: string) => [...platformKeys.all, 'feature-flags', key] as const,
  adminOverview: () => [...platformKeys.all, 'admin', 'overview'] as const,
  adminHealth: () => [...platformKeys.all, 'admin', 'health'] as const,
  adminProviders: () => [...platformKeys.all, 'admin', 'providers'] as const,
  adminAuditLogs: (limit?: number) => [...platformKeys.all, 'admin', 'audit-logs', limit] as const,
  adminBilling: () => [...platformKeys.all, 'admin', 'billing'] as const,
  adminUsage: () => [...platformKeys.all, 'admin', 'usage'] as const,
}

// ---------------------------------------------------------------------------
// Analytics hooks
// ---------------------------------------------------------------------------
export function useAnalyticsSummary(params?: { user_id?: string; start?: string; end?: string }) {
  return useQuery<AnalyticsSummaryDTO, ApiError>({
    queryKey: platformKeys.analyticsSummary(params),
    queryFn: () => getSDK().platform.getAnalyticsSummary(params),
  })
}

export function useCostBreakdown(params?: { start?: string; end?: string; revenue?: number }) {
  return useQuery<CostBreakdownDTO, ApiError>({
    queryKey: platformKeys.costBreakdown(params),
    queryFn: () => getSDK().platform.getCostBreakdown(params),
  })
}

// ---------------------------------------------------------------------------
// Usage hooks
// ---------------------------------------------------------------------------
export function useUsageSummary(userId: string) {
  return useQuery<UsageSummaryDTO, ApiError>({
    queryKey: platformKeys.usage(userId),
    queryFn: () => getSDK().platform.getUsageSummary(userId),
    enabled: !!userId,
  })
}

// ---------------------------------------------------------------------------
// Billing — Plans
// ---------------------------------------------------------------------------
export function usePlans() {
  return useQuery<PlanDTO[], ApiError>({
    queryKey: platformKeys.plans(),
    queryFn: () => getSDK().platform.listPlans(),
  })
}

// ---------------------------------------------------------------------------
// Billing — Subscriptions
// ---------------------------------------------------------------------------
export function useSubscription(userId: string) {
  return useQuery<SubscriptionDTO | null, ApiError>({
    queryKey: platformKeys.subscription(userId),
    queryFn: () => getSDK().platform.getSubscription(userId),
    enabled: !!userId,
  })
}

export function useCreateSubscription() {
  const qc = useQueryClient()
  return useMutation<SubscriptionDTO, ApiError, { userId: string; body: CreateSubscriptionRequest }>({
    mutationFn: ({ userId, body }) => getSDK().platform.createSubscription(userId, body),
    onSuccess: (_, { userId }) => {
      qc.invalidateQueries({ queryKey: platformKeys.subscription(userId) })
    },
  })
}

export function useCancelSubscription() {
  const qc = useQueryClient()
  return useMutation<SubscriptionDTO | null, ApiError, string>({
    mutationFn: (userId) => getSDK().platform.cancelSubscription(userId),
    onSuccess: (_, userId) => {
      qc.invalidateQueries({ queryKey: platformKeys.subscription(userId) })
    },
  })
}

export function useChangePlan() {
  const qc = useQueryClient()
  return useMutation<SubscriptionDTO, ApiError, { userId: string; planId: string }>({
    mutationFn: ({ userId, planId }) => getSDK().platform.changePlan(userId, planId),
    onSuccess: (_, { userId }) => {
      qc.invalidateQueries({ queryKey: platformKeys.subscription(userId) })
    },
  })
}

// ---------------------------------------------------------------------------
// Billing — Credits
// ---------------------------------------------------------------------------
export function useCreditBalance(userId: string) {
  return useQuery<CreditBalanceDTO, ApiError>({
    queryKey: platformKeys.credits(userId),
    queryFn: () => getSDK().platform.getCreditBalance(userId),
    enabled: !!userId,
  })
}

export function useAddCredits() {
  const qc = useQueryClient()
  return useMutation<CreditBalanceDTO, ApiError, { userId: string; body: AddCreditsRequest }>({
    mutationFn: ({ userId, body }) => getSDK().platform.addCredits(userId, body),
    onSuccess: (_, { userId }) => {
      qc.invalidateQueries({ queryKey: platformKeys.credits(userId) })
    },
  })
}

// ---------------------------------------------------------------------------
// Billing — Invoices
// ---------------------------------------------------------------------------
export function useInvoices(userId?: string) {
  return useQuery<InvoiceDTO[], ApiError>({
    queryKey: platformKeys.invoices(userId),
    queryFn: () => getSDK().platform.listInvoices(userId),
  })
}

export function usePayInvoice() {
  const qc = useQueryClient()
  return useMutation<InvoiceDTO | null, ApiError, string>({
    mutationFn: (invoiceId) => getSDK().platform.payInvoice(invoiceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.invoices() })
    },
  })
}

// ---------------------------------------------------------------------------
// Organizations
// ---------------------------------------------------------------------------
export function useOrganizations(userId?: string) {
  return useQuery<OrganizationDTO[], ApiError>({
    queryKey: platformKeys.organizations(userId),
    queryFn: () => getSDK().platform.listOrganizations(userId),
  })
}

export function useCreateOrganization() {
  const qc = useQueryClient()
  return useMutation<OrganizationDTO, ApiError, CreateOrganizationRequest>({
    mutationFn: (body) => getSDK().platform.createOrganization(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.organizations() })
    },
  })
}

export function useOrganization(orgId: string) {
  return useQuery<OrganizationDTO, ApiError>({
    queryKey: platformKeys.organization(orgId),
    queryFn: () => getSDK().platform.getOrganization(orgId),
    enabled: !!orgId,
  })
}

export function useMembers(orgId: string) {
  return useQuery<TeamMemberDTO[], ApiError>({
    queryKey: platformKeys.members(orgId),
    queryFn: () => getSDK().platform.listMembers(orgId),
    enabled: !!orgId,
  })
}

export function useAddMember() {
  const qc = useQueryClient()
  return useMutation<TeamMemberDTO | null, ApiError, { orgId: string; userId: string; role?: string }>({
    mutationFn: ({ orgId, userId, role }) => getSDK().platform.addMember(orgId, userId, role),
    onSuccess: (_, { orgId }) => {
      qc.invalidateQueries({ queryKey: platformKeys.members(orgId) })
    },
  })
}

// ---------------------------------------------------------------------------
// Feature Flags
// ---------------------------------------------------------------------------
export function useFeatureFlags(scope?: string) {
  return useQuery<FeatureFlagDTO[], ApiError>({
    queryKey: platformKeys.featureFlags(scope),
    queryFn: () => getSDK().platform.listFeatureFlags(scope),
  })
}

export function useFeatureFlag(key: string) {
  return useQuery<FeatureFlagDTO, ApiError>({
    queryKey: platformKeys.featureFlag(key),
    queryFn: () => getSDK().platform.getFeatureFlag(key),
    enabled: !!key,
  })
}

export function useCreateFeatureFlag() {
  const qc = useQueryClient()
  return useMutation<FeatureFlagDTO, ApiError, CreateFeatureFlagRequest>({
    mutationFn: (body) => getSDK().platform.createFeatureFlag(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.featureFlags() })
    },
  })
}

export function useUpdateFeatureFlag() {
  const qc = useQueryClient()
  return useMutation<FeatureFlagDTO, ApiError, { key: string; body: Partial<CreateFeatureFlagRequest> }>({
    mutationFn: ({ key, body }) => getSDK().platform.updateFeatureFlag(key, body),
    onSuccess: (_, { key }) => {
      qc.invalidateQueries({ queryKey: platformKeys.featureFlags() })
      qc.invalidateQueries({ queryKey: platformKeys.featureFlag(key) })
    },
  })
}

export function useDeleteFeatureFlag() {
  const qc = useQueryClient()
  return useMutation<MessageResponse, ApiError, string>({
    mutationFn: (key) => getSDK().platform.deleteFeatureFlag(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.featureFlags() })
    },
  })
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export function usePlatformOverview() {
  return useQuery<PlatformOverviewDTO, ApiError>({
    queryKey: platformKeys.adminOverview(),
    queryFn: () => getSDK().platform.getPlatformOverview(),
  })
}

export function useSystemHealth() {
  return useQuery<HealthReportDTO, ApiError>({
    queryKey: platformKeys.adminHealth(),
    queryFn: () => getSDK().platform.getSystemHealth(),
    refetchInterval: 30000,
  })
}

export function useProviderHealth() {
  return useQuery<Record<string, unknown>, ApiError>({
    queryKey: platformKeys.adminProviders(),
    queryFn: () => getSDK().platform.getProviderHealth(),
    refetchInterval: 30000,
  })
}

export function useAuditLogs(limit?: number) {
  return useQuery<AuditEntryDTO[], ApiError>({
    queryKey: platformKeys.adminAuditLogs(limit),
    queryFn: () => getSDK().platform.getAuditLogs(limit),
  })
}

export function useAdminBilling() {
  return useQuery<Record<string, unknown>, ApiError>({
    queryKey: platformKeys.adminBilling(),
    queryFn: () => getSDK().platform.getBillingOverview(),
  })
}

export function useAdminUsage() {
  return useQuery<Record<string, unknown>, ApiError>({
    queryKey: platformKeys.adminUsage(),
    queryFn: () => getSDK().platform.getUsageDashboard(),
  })
}

export function useSuspendUser() {
  const qc = useQueryClient()
  return useMutation<MessageResponse, ApiError, string>({
    mutationFn: (userId) => getSDK().platform.suspendUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.adminOverview() })
    },
  })
}

export function useActivateUser() {
  const qc = useQueryClient()
  return useMutation<MessageResponse, ApiError, string>({
    mutationFn: (userId) => getSDK().platform.activateUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: platformKeys.adminOverview() })
    },
  })
}

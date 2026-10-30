import type { ApiClient } from '../api-client'
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
  MonitoringSnapshotDTO,
  AuditEntryDTO,
  CreateSubscriptionRequest,
  AddCreditsRequest,
  CreateOrganizationRequest,
  CreateFeatureFlagRequest,
  MessageResponse,
} from '@ai-video-studio/shared-types'

export class PlatformModuleSDK {
  constructor(private readonly api: ApiClient) {}

  // ------------------------------------------------------------------
  // Analytics
  // ------------------------------------------------------------------
  async getAnalyticsSummary(params?: {
    user_id?: string
    start?: string
    end?: string
  }): Promise<AnalyticsSummaryDTO> {
    return this.api.get<AnalyticsSummaryDTO>('/platform/analytics/summary', params)
  }

  async getCostBreakdown(params?: {
    start?: string
    end?: string
    revenue?: number
  }): Promise<CostBreakdownDTO> {
    return this.api.get<CostBreakdownDTO>('/platform/analytics/costs', params)
  }

  // ------------------------------------------------------------------
  // Usage
  // ------------------------------------------------------------------
  async getUsageSummary(userId: string): Promise<UsageSummaryDTO> {
    return this.api.get<UsageSummaryDTO>(`/platform/usage/${userId}`)
  }

  // ------------------------------------------------------------------
  // Billing — Plans
  // ------------------------------------------------------------------
  async listPlans(): Promise<PlanDTO[]> {
    return this.api.get<PlanDTO[]>('/platform/billing/plans')
  }

  async getPlan(planId: string): Promise<PlanDTO> {
    return this.api.get<PlanDTO>(`/platform/billing/plans/${planId}`)
  }

  // ------------------------------------------------------------------
  // Billing — Subscriptions
  // ------------------------------------------------------------------
  async getSubscription(userId: string): Promise<SubscriptionDTO | null> {
    return this.api.get<SubscriptionDTO | null>(`/platform/billing/subscriptions/${userId}`)
  }

  async createSubscription(userId: string, body: CreateSubscriptionRequest): Promise<SubscriptionDTO> {
    return this.api.post<SubscriptionDTO>('/platform/billing/subscriptions', { user_id: userId, ...body })
  }

  async cancelSubscription(userId: string): Promise<SubscriptionDTO | null> {
    return this.api.post<SubscriptionDTO | null>(`/platform/billing/subscriptions/${userId}/cancel`)
  }

  async changePlan(userId: string, planId: string): Promise<SubscriptionDTO> {
    return this.api.patch<SubscriptionDTO>(`/platform/billing/subscriptions/${userId}`, { plan_id: planId })
  }

  // ------------------------------------------------------------------
  // Billing — Credits
  // ------------------------------------------------------------------
  async getCreditBalance(userId: string): Promise<CreditBalanceDTO> {
    return this.api.get<CreditBalanceDTO>(`/platform/billing/credits/${userId}`)
  }

  async addCredits(userId: string, body: AddCreditsRequest): Promise<CreditBalanceDTO> {
    return this.api.post<CreditBalanceDTO>(`/platform/billing/credits/${userId}/add`, body)
  }

  // ------------------------------------------------------------------
  // Billing — Invoices
  // ------------------------------------------------------------------
  async listInvoices(userId?: string): Promise<InvoiceDTO[]> {
    return this.api.get<InvoiceDTO[]>('/platform/billing/invoices', userId ? { user_id: userId } : undefined)
  }

  async payInvoice(invoiceId: string): Promise<InvoiceDTO | null> {
    return this.api.post<InvoiceDTO | null>(`/platform/billing/invoices/${invoiceId}/pay`)
  }

  // ------------------------------------------------------------------
  // Organizations
  // ------------------------------------------------------------------
  async listOrganizations(userId?: string): Promise<OrganizationDTO[]> {
    return this.api.get<OrganizationDTO[]>('/platform/organizations', userId ? { user_id: userId } : undefined)
  }

  async createOrganization(body: CreateOrganizationRequest): Promise<OrganizationDTO> {
    return this.api.post<OrganizationDTO>('/platform/organizations', body)
  }

  async getOrganization(orgId: string): Promise<OrganizationDTO> {
    return this.api.get<OrganizationDTO>(`/platform/organizations/${orgId}`)
  }

  async listMembers(orgId: string): Promise<TeamMemberDTO[]> {
    return this.api.get<TeamMemberDTO[]>(`/platform/organizations/${orgId}/members`)
  }

  async addMember(orgId: string, userId: string, role?: string): Promise<TeamMemberDTO | null> {
    return this.api.post<TeamMemberDTO | null>(`/platform/organizations/${orgId}/members`, {
      user_id: userId,
      role: role ?? 'member',
    })
  }

  // ------------------------------------------------------------------
  // Feature Flags
  // ------------------------------------------------------------------
  async listFeatureFlags(scope?: string): Promise<FeatureFlagDTO[]> {
    return this.api.get<FeatureFlagDTO[]>('/platform/feature-flags', scope ? { scope } : undefined)
  }

  async getFeatureFlag(key: string): Promise<FeatureFlagDTO> {
    return this.api.get<FeatureFlagDTO>(`/platform/feature-flags/${key}`)
  }

  async createFeatureFlag(body: CreateFeatureFlagRequest): Promise<FeatureFlagDTO> {
    return this.api.post<FeatureFlagDTO>('/platform/feature-flags', body)
  }

  async updateFeatureFlag(key: string, body: Partial<CreateFeatureFlagRequest>): Promise<FeatureFlagDTO> {
    return this.api.patch<FeatureFlagDTO>(`/platform/feature-flags/${key}`, body)
  }

  async deleteFeatureFlag(key: string): Promise<MessageResponse> {
    return this.api.delete<MessageResponse>(`/platform/feature-flags/${key}`)
  }

  // ------------------------------------------------------------------
  // Admin
  // ------------------------------------------------------------------
  async getPlatformOverview(): Promise<PlatformOverviewDTO> {
    return this.api.get<PlatformOverviewDTO>('/platform/admin/overview')
  }

  async getSystemHealth(): Promise<HealthReportDTO> {
    return this.api.get<HealthReportDTO>('/platform/admin/health')
  }

  async getProviderHealth(): Promise<Record<string, unknown>> {
    return this.api.get<Record<string, unknown>>('/platform/admin/providers')
  }

  async getAuditLogs(limit?: number): Promise<AuditEntryDTO[]> {
    return this.api.get<AuditEntryDTO[]>('/platform/admin/audit-logs', limit ? { limit } : undefined)
  }

  async getBillingOverview(): Promise<Record<string, unknown>> {
    return this.api.get<Record<string, unknown>>('/platform/admin/billing')
  }

  async getUsageDashboard(): Promise<Record<string, unknown>> {
    return this.api.get<Record<string, unknown>>('/platform/admin/usage')
  }

  async suspendUser(userId: string): Promise<MessageResponse> {
    return this.api.post<MessageResponse>(`/platform/admin/users/${userId}/suspend`)
  }

  async activateUser(userId: string): Promise<MessageResponse> {
    return this.api.post<MessageResponse>(`/platform/admin/users/${userId}/activate`)
  }
}

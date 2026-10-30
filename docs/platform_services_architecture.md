# Platform Services, Analytics & SaaS Foundation — Architecture

## Overview

The Platform Services Layer (Phase 12) provides reusable infrastructure
that powers every module of the application. It remains **independent**
from content generation logic.

## Architecture

```
Application
    │
    ▼
Platform Services (src/platform/)
    │
    ├── Analytics Service ────── Project metrics, success rates, provider usage
    ├── Usage Tracker ────────── Resource consumption tracking
    ├── Billing Service ──────── Plans, credits, subscriptions, invoices
    ├── Cost Analytics ───────── Cost breakdowns per project/user/provider
    ├── Organization Service ─── Orgs, teams, members, invitations, collaboration
    ├── Notification Service ─── Email, in-app, webhook notifications
    ├── Feature Flag Service ─── Toggles, beta features, A/B testing
    ├── Platform Audit Service ─ Append-only audit log for all platform actions
    ├── Monitoring Service ───── Latency, queue size, failures, resource usage
    ├── Health Service ───────── Component health checks (db, redis, providers)
    ├── Metrics Service ──────── Business, technical, financial, operational
    ├── API Management ───────── API keys, rate limits, quotas
    └── Admin Service ────────── Aggregated dashboard, user management, support
```

## Key Design Decisions

### 1. Independence from Content Generation

All platform services live in `src/platform/` and have no dependencies
on `src/research/`, `src/script/`, `src/storyboard/`, `src/generation/`,
`src/composition/`, or `src/publishing/`. They consume data through
interfaces and generic models.

### 2. Extensible Interfaces

- **Billing**: Stripe integration deferred — `BillingService` provides
  plan/credit/invoice abstractions ready for a `PaymentProvider` interface
- **Notifications**: Email/Slack/Discord/Teams deferred —
  `NotificationService.register_handler()` allows plugging in providers
- **Feature Flags**: Experimentation platform deferred —
  `FeatureFlagService` supports boolean, percentage, and variant flags
- **API Management**: Developer portal deferred —
  `ApiManagementService` provides keys, rate limits, quotas

### 3. Complementing Existing Services

The platform layer complements existing Phase 1 services:
- `EventBus` (Phase 1) → Platform services subscribe to events for analytics
- `CostTracker` (Phase 1) → `CostAnalyticsService` provides higher-level aggregation
- `AuditService` (Phase 2) → `PlatformAuditService` covers platform-level actions
- `ConfigService` feature flags (Phase 1) → `FeatureFlagService` adds multi-scope, A/B testing

### 4. Dependency Injection

`AdminService` accepts all services via constructor injection, enabling
easy testing and future DI container integration.

## Service Details

### Analytics Service

Tracks project lifecycle metrics:
- Generation, publishing, rendering time
- Success/failure rates
- Most used providers and top models
- Project growth (30-day trend)
- User activity rankings

### Usage Tracker

Records resource consumption with convenience methods:
- `record_image_generation()`, `record_video_generation()`
- `record_voice_minutes()`, `record_rendering_minutes()`
- `record_storage()`, `record_publishing()`, `record_tokens()`

Provides per-user and per-org aggregated summaries.

### Billing Service

Three default plans (Free, Pro, Enterprise) with feature limits:
- Plan management (CRUD + custom plans)
- Subscription lifecycle (create, cancel, change plan, trial)
- Credit system (add, consume, check balance)
- Invoice generation and payment tracking
- Plan limit checking (`check_plan_limits()`)

### Cost Analytics

Multi-dimensional cost tracking:
- Per project, user, provider, asset, workflow
- Daily and monthly cost aggregation
- Profit margin calculation (revenue vs cost)

### Organization Service

Full organization lifecycle:
- Create, update, delete organizations
- Add/remove members with role management
- Ownership transfer
- Invitation system (create, accept, decline, revoke)
- Team collaboration: project sharing, comments, approvals, activity feed

### Notification Service

Multi-channel notifications:
- Email, in-app, webhook channels
- Batch sending
- Read/dismiss tracking
- Webhook registration and management
- Handler registration for future providers (Slack, Discord, Teams)

### Feature Flag Service

Multi-scope feature flags:
- Global, user, organization, plan scopes
- Boolean, percentage rollout, A/B variant types
- Deterministic variant assignment (hash-based)
- Enable/disable per user or org

### Platform Audit Service

Append-only audit log:
- Publishing, generation, deletion, billing, admin, role, settings changes
- Query by user, org, action, resource type
- Resource history tracking
- Action count aggregation

### Monitoring Service

System metrics collection:
- Latency, queue size, failures, retries
- Provider availability
- Memory, CPU, disk usage
- Snapshot-based monitoring
- Metric history

### Health Service

Component health checks:
- Register custom health checkers
- Check individual components or all at once
- Overall status: healthy, degraded, unhealthy
- Standard components: generation, rendering, publishing, database, redis, storage, AI providers

### Metrics Service

Categorized metric collection:
- Business, technical, performance, financial, operational
- Counter, gauge, histogram, summary types
- Aggregated summaries by category
- Metric name discovery

### API Management

API key and quota management:
- Create, revoke, delete API keys
- Key validation by value
- Rate limiting (per minute, per day, burst)
- Quota setting and tracking
- Usage reports

### Admin Service

Administrative dashboard:
- Platform overview (aggregated metrics from all services)
- User overview (usage, subscription, credits)
- Provider health
- System health
- Billing overview
- Recent audit logs
- User suspension/activation

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Platform Services Layer                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ Analytics     │  │ Usage        │  │  Billing Service      │     │
│  │ Service       │  │ Tracker      │  │  (plans, credits,     │     │
│  └──────────────┘  └──────────────┘  │   invoices)           │     │
│                                      └───────────────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ Cost          │  │ Organization │  │  Notification         │     │
│  │ Analytics     │  │ Service      │  │  Service              │     │
│  └──────────────┘  └──────────────┘  └───────────────────────┘     │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ Feature Flag  │  │ Platform     │  │  Monitoring Service   │     │
│  │ Service       │  │ Audit        │  │  + Health Service     │     │
│  └──────────────┘  └──────────────┘  └───────────────────────┘     │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ Metrics       │  │ API          │  │  Admin Service         │     │
│  │ Service       │  │ Management   │  │  (aggregated dashboard)│    │
│  └──────────────┘  └──────────────┘  └───────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
         │                                              │
         ▼                                              ▼
    Existing Services                           Content Generation
    (EventBus, CostTracker,                    (Research, Script,
     AuditService, ConfigService)               Storyboard, Generation,
                                                Composition, Publishing)
```

## File Structure

```
src/platform/
├── __init__.py            # All exports
├── schema.py              # All Pydantic v2 models and enums
├── analytics.py           # AnalyticsService
├── usage.py               # UsageTracker
├── billing.py             # BillingService
├── cost_analytics.py      # CostAnalyticsService
├── organization.py        # OrganizationService
├── notification.py        # NotificationService
├── feature_flags.py       # FeatureFlagService
├── audit.py               # PlatformAuditService
├── monitoring.py          # MonitoringService + HealthService
├── metrics.py             # MetricsService
├── api_management.py      # ApiManagementService
└── admin.py               # AdminService
```

## Future Extensions

| Feature | Current | Future |
|---------|---------|--------|
| Billing | Plan/credit/invoice abstractions | Stripe integration via `PaymentProvider` interface |
| Notifications | Email/in-app/webhook handlers | Slack, Discord, Teams providers |
| Feature Flags | Boolean/percentage/variant | Experimentation platform with statistical analysis |
| API Management | Keys, rate limits, quotas | Developer portal with documentation |
| Monitoring | In-memory metrics | Prometheus/Grafana integration |
| Health | Custom checkers | Kubernetes liveness/readiness probes |
| Organizations | Single-org per user | Multi-org, org hierarchies |
| Collaboration | Comments, approvals | Real-time collaboration (WebSocket) |

## Testing

192 tests in `tests/unit/test_platform_services.py` covering:
- Schema models, enums, defaults, computed properties
- Analytics service (record, summary, filtering, user activity)
- Usage tracker (all resource types, per-user/org summaries)
- Billing service (plans, subscriptions, credits, invoices, plan limits)
- Cost analytics (breakdowns, daily/monthly, profit margin)
- Organization service (CRUD, members, invitations, collaboration, activity feed)
- Notification service (send, batch, read/dismiss, webhooks)
- Feature flag service (all scopes, types, enable/disable, variants)
- Platform audit service (record, query, filter, count)
- Monitoring service (metrics, snapshots, resource usage)
- Health service (register, check, overall status)
- Metrics service (all categories, summary, names)
- API management (keys, rate limits, quotas, usage reports)
- Admin service (overview, user view, health, billing, logs)
- Integration (full platform workflow, billing+usage, org+notifications)

// =============================================================================
// Shared Types — Feature Registry, Plugin System, Realtime Events
// =============================================================================

// -----------------------------------------------------------------------------
// Feature Registry
// -----------------------------------------------------------------------------
export interface FeatureManifest {
  id: string
  name: string
  description: string
  icon?: string
  enabled: boolean
  route?: string
  order: number
  permissions?: string[]
  beta?: boolean
  pluginId?: string
}

export interface FeatureRegistryEntry {
  manifest: FeatureManifest
  loader?: () => Promise<{ default: unknown }>
  component?: unknown
}

// -----------------------------------------------------------------------------
// Plugin System
// -----------------------------------------------------------------------------
export interface PluginManifest {
  id: string
  name: string
  version: string
  description: string
  author: string
  icon?: string
  enabled: boolean
  permissions: string[]
  features: string[]
  config?: Record<string, unknown>
}

export interface PluginContext {
  api: unknown
  eventBus: unknown
  featureRegistry: unknown
  logger: (level: string, message: string, data?: unknown) => void
}

export interface Plugin {
  manifest: PluginManifest
  install: (context: PluginContext) => Promise<void>
  uninstall?: () => Promise<void>
}

// -----------------------------------------------------------------------------
// Realtime Events
// -----------------------------------------------------------------------------
export enum RealtimeEventType {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
  PROJECT_UPDATED = 'project_updated',
  GENERATION_PROGRESS = 'generation_progress',
  RENDERING_PROGRESS = 'rendering_progress',
  PUBLISHING_PROGRESS = 'publishing_progress',
  NOTIFICATION = 'notification',
  PRESENCE = 'presence',
}

export interface RealtimeEvent<T = unknown> {
  type: RealtimeEventType | string
  data: T
  timestamp: string
  correlation_id?: string
}

export type RealtimeEventHandler<T = unknown> = (event: RealtimeEvent<T>) => void

// -----------------------------------------------------------------------------
// Command Palette
// -----------------------------------------------------------------------------
export interface CommandItem {
  id: string
  label: string
  shortcut?: string
  icon?: string
  group: string
  keywords?: string[]
  action: () => void | Promise<void>
  disabled?: boolean
}

// -----------------------------------------------------------------------------
// Navigation
// -----------------------------------------------------------------------------
export interface NavItem {
  label: string
  href: string
  icon?: string
  badge?: string | number
  children?: NavItem[]
  permissions?: string[]
}

export interface BreadcrumbItem {
  label: string
  href?: string
}

// -----------------------------------------------------------------------------
// Theme
// -----------------------------------------------------------------------------
export type ThemeMode = 'light' | 'dark' | 'system'

export interface ThemeConfig {
  mode: ThemeMode
  resolvedMode: 'light' | 'dark'
}

// -----------------------------------------------------------------------------
// Environment Configuration
// -----------------------------------------------------------------------------
export interface EnvironmentConfig {
  apiBaseUrl: string
  wsUrl?: string
  appName?: string
  appVersion?: string
  environment: 'development' | 'staging' | 'production'
  sentryDsn?: string
  analyticsKey?: string
}

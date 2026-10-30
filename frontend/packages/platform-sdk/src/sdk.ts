import { ApiClient, type ApiClientConfig } from './api-client'
import { AuthSDK } from './modules/auth'
import { UsersSDK } from './modules/users'
import { ApiKeysSDK } from './modules/api-keys'
import { SessionsSDK } from './modules/sessions'
import { ProjectsSDK } from './modules/projects'
import { ProductionSDK } from './modules/production'
import { PlatformModuleSDK } from './modules/platform'

export class PlatformSDK {
  readonly api: ApiClient
  readonly auth: AuthSDK
  readonly users: UsersSDK
  readonly apiKeys: ApiKeysSDK
  readonly sessions: SessionsSDK
  readonly projects: ProjectsSDK
  readonly production: ProductionSDK
  readonly platform: PlatformModuleSDK

  constructor(config: ApiClientConfig) {
    this.api = new ApiClient(config)
    this.auth = new AuthSDK(this.api)
    this.users = new UsersSDK(this.api)
    this.apiKeys = new ApiKeysSDK(this.api)
    this.sessions = new SessionsSDK(this.api)
    this.projects = new ProjectsSDK(this.api)
    this.production = new ProductionSDK(this.api)
    this.platform = new PlatformModuleSDK(this.api)
  }
}

let sdkInstance: PlatformSDK | null = null

export function initSDK(config: ApiClientConfig): PlatformSDK {
  sdkInstance = new PlatformSDK(config)
  return sdkInstance
}

export function getSDK(): PlatformSDK {
  if (!sdkInstance) {
    throw new Error('SDK not initialized. Call initSDK() first.')
  }
  return sdkInstance
}

export type { ApiClientConfig } from './api-client'

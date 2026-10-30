import type { PluginDefinition, PluginContext, PluginLifecycle } from '@ai-video-studio/shared-types'
import { featureRegistry } from './feature-registry'

class PluginManagerImpl {
  private plugins = new Map<string, PluginDefinition>()
  private instances = new Map<string, PluginLifecycle>()
  private context: PluginContext | null = null

  setContext(context: PluginContext): void {
    this.context = context
  }

  async register(plugin: PluginDefinition): Promise<void> {
    if (this.plugins.has(plugin.id)) {
      console.warn(`Plugin "${plugin.id}" is already registered`)
      return
    }

    this.plugins.set(plugin.id, plugin)

    if (plugin.features) {
      for (const feature of plugin.features) {
        featureRegistry.register(feature)
      }
    }

    if (plugin.onInstall && this.context) {
      await plugin.onInstall(this.context)
    }

    const lifecycle: PluginLifecycle = { installed: true }
    this.instances.set(plugin.id, lifecycle)
  }

  async activate(id: string): Promise<void> {
    const plugin = this.plugins.get(id)
    if (!plugin) {
      console.warn(`Plugin "${id}" not found`)
      return
    }

    const instance = this.instances.get(id)
    if (!instance?.installed) {
      console.warn(`Plugin "${id}" is not installed`)
      return
    }

    if (instance.active) {
      console.warn(`Plugin "${id}" is already active`)
      return
    }

    if (plugin.onActivate && this.context) {
      await plugin.onActivate(this.context)
    }

    this.instances.set(id, { ...instance, active: true })
  }

  async deactivate(id: string): Promise<void> {
    const plugin = this.plugins.get(id)
    if (!plugin) return

    const instance = this.instances.get(id)
    if (!instance?.active) return

    if (plugin.onDeactivate && this.context) {
      await plugin.onDeactivate(this.context)
    }

    this.instances.set(id, { ...instance, active: false })
  }

  async uninstall(id: string): Promise<void> {
    const plugin = this.plugins.get(id)
    if (!plugin) return

    await this.deactivate(id)

    if (plugin.onUninstall && this.context) {
      await plugin.onUninstall(this.context)
    }

    if (plugin.features) {
      for (const feature of plugin.features) {
        featureRegistry.unregister(feature.id)
      }
    }

    this.plugins.delete(id)
    this.instances.delete(id)
  }

  get(id: string): PluginDefinition | undefined {
    return this.plugins.get(id)
  }

  getAll(): PluginDefinition[] {
    return Array.from(this.plugins.values())
  }

  getActive(): PluginDefinition[] {
    return this.getAll().filter((p) => this.instances.get(p.id)?.active)
  }

  isInstalled(id: string): boolean {
    return this.instances.get(id)?.installed ?? false
  }

  isActive(id: string): boolean {
    return this.instances.get(id)?.active ?? false
  }

  clear(): void {
    this.plugins.clear()
    this.instances.clear()
  }
}

export const pluginManager = new PluginManagerImpl()

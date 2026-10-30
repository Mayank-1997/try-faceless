import { describe, it, expect, beforeEach } from 'vitest'
import { pluginManager } from '../plugin-manager'
import { featureRegistry } from '../feature-registry'
import type { PluginDefinition, PluginContext } from '@ai-video-studio/shared-types'

const mockContext: PluginContext = {
  config: {
    apiBaseUrl: 'http://localhost:8000/api/v1',
    wsUrl: 'ws://localhost:8000/ws',
    appName: 'Test',
    appVersion: '0.0.0',
    environment: 'development',
  },
  realtime: {
    connect: () => {},
    disconnect: () => {},
    on: () => () => {},
    off: () => {},
    emit: () => {},
    send: () => {},
    isConnected: () => false,
  },
}

describe('PluginManager', () => {
  beforeEach(() => {
    pluginManager.clear()
    featureRegistry.clear()
    pluginManager.setContext(mockContext)
  })

  it('should register a plugin', async () => {
    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
    }
    await pluginManager.register(plugin)
    expect(pluginManager.isInstalled('test-plugin')).toBe(true)
    expect(pluginManager.get('test-plugin')).toEqual(plugin)
  })

  it('should not register duplicate plugins', async () => {
    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
    }
    await pluginManager.register(plugin)
    await pluginManager.register(plugin)
    expect(pluginManager.getAll()).toHaveLength(1)
  })

  it('should activate and deactivate plugins', async () => {
    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
    }
    await pluginManager.register(plugin)
    await pluginManager.activate('test-plugin')
    expect(pluginManager.isActive('test-plugin')).toBe(true)
    await pluginManager.deactivate('test-plugin')
    expect(pluginManager.isActive('test-plugin')).toBe(false)
  })

  it('should call lifecycle hooks', async () => {
    const onInstall = vi.fn()
    const onActivate = vi.fn()
    const onDeactivate = vi.fn()
    const onUninstall = vi.fn()

    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
      onInstall,
      onActivate,
      onDeactivate,
      onUninstall,
    }
    await pluginManager.register(plugin)
    expect(onInstall).toHaveBeenCalledTimes(1)
    await pluginManager.activate('test-plugin')
    expect(onActivate).toHaveBeenCalledTimes(1)
    await pluginManager.deactivate('test-plugin')
    expect(onDeactivate).toHaveBeenCalledTimes(1)
    await pluginManager.uninstall('test-plugin')
    expect(onUninstall).toHaveBeenCalledTimes(1)
  })

  it('should register features on install', async () => {
    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
      features: [
        {
          id: 'test-feature',
          name: 'Test Feature',
          description: '',
          enabled: true,
          status: 'stable',
          version: '1.0.0',
        },
      ],
    }
    await pluginManager.register(plugin)
    expect(featureRegistry.get('test-feature')).toBeDefined()
  })

  it('should unregister features on uninstall', async () => {
    const plugin: PluginDefinition = {
      id: 'test-plugin',
      name: 'Test Plugin',
      version: '1.0.0',
      description: 'A test plugin',
      features: [
        {
          id: 'test-feature',
          name: 'Test Feature',
          description: '',
          enabled: true,
          status: 'stable',
          version: '1.0.0',
        },
      ],
    }
    await pluginManager.register(plugin)
    await pluginManager.uninstall('test-plugin')
    expect(featureRegistry.get('test-feature')).toBeUndefined()
  })
})

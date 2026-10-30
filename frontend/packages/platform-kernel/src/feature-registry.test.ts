import { describe, it, expect, beforeEach } from 'vitest'
import { featureRegistry } from '../feature-registry'
import type { FeatureDefinition } from '@ai-video-studio/shared-types'

describe('FeatureRegistry', () => {
  beforeEach(() => {
    featureRegistry.clear()
  })

  it('should register a feature', () => {
    const feature: FeatureDefinition = {
      id: 'test-feature',
      name: 'Test Feature',
      description: 'A test feature',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    }
    featureRegistry.register(feature)
    expect(featureRegistry.get('test-feature')).toEqual(feature)
  })

  it('should unregister a feature', () => {
    const feature: FeatureDefinition = {
      id: 'test-feature',
      name: 'Test Feature',
      description: 'A test feature',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    }
    featureRegistry.register(feature)
    featureRegistry.unregister('test-feature')
    expect(featureRegistry.get('test-feature')).toBeUndefined()
  })

  it('should check if feature is enabled', () => {
    const feature: FeatureDefinition = {
      id: 'test-feature',
      name: 'Test Feature',
      description: 'A test feature',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    }
    featureRegistry.register(feature)
    expect(featureRegistry.isEnabled('test-feature')).toBe(true)
    expect(featureRegistry.isEnabled('nonexistent')).toBe(false)
  })

  it('should get all enabled features', () => {
    featureRegistry.register({
      id: 'enabled-1',
      name: 'Enabled 1',
      description: '',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    })
    featureRegistry.register({
      id: 'disabled-1',
      name: 'Disabled 1',
      description: '',
      enabled: false,
      status: 'stable',
      version: '1.0.0',
    })
    const enabled = featureRegistry.getEnabled()
    expect(enabled).toHaveLength(1)
    expect(enabled[0].id).toBe('enabled-1')
  })

  it('should enable/disable features', () => {
    featureRegistry.register({
      id: 'test-feature',
      name: 'Test',
      description: '',
      enabled: false,
      status: 'stable',
      version: '1.0.0',
    })
    expect(featureRegistry.isEnabled('test-feature')).toBe(false)
    featureRegistry.enable('test-feature')
    expect(featureRegistry.isEnabled('test-feature')).toBe(true)
    featureRegistry.disable('test-feature')
    expect(featureRegistry.isEnabled('test-feature')).toBe(false)
  })

  it('should notify subscribers on change', () => {
    let callCount = 0
    const unsubscribe = featureRegistry.subscribe(() => {
      callCount++
    })
    featureRegistry.register({
      id: 'test',
      name: 'Test',
      description: '',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    })
    expect(callCount).toBe(1)
    featureRegistry.unregister('test')
    expect(callCount).toBe(2)
    unsubscribe()
    featureRegistry.register({
      id: 'test2',
      name: 'Test 2',
      description: '',
      enabled: true,
      status: 'stable',
      version: '1.0.0',
    })
    expect(callCount).toBe(2)
  })
})

import type { FeatureDefinition, FeatureStatus } from '@ai-video-studio/shared-types'

class FeatureRegistryImpl {
  private features = new Map<string, FeatureDefinition>()
  private listeners = new Set<() => void>()

  register(feature: FeatureDefinition): void {
    this.features.set(feature.id, feature)
    this.notifyListeners()
  }

  unregister(id: string): void {
    this.features.delete(id)
    this.notifyListeners()
  }

  get(id: string): FeatureDefinition | undefined {
    return this.features.get(id)
  }

  getAll(): FeatureDefinition[] {
    return Array.from(this.features.values())
  }

  getEnabled(): FeatureDefinition[] {
    return this.getAll().filter((f) => f.enabled)
  }

  isEnabled(id: string): boolean {
    return this.features.get(id)?.enabled ?? false
  }

  setStatus(id: string, status: FeatureStatus): void {
    const feature = this.features.get(id)
    if (feature) {
      this.features.set(id, { ...feature, status })
      this.notifyListeners()
    }
  }

  enable(id: string): void {
    const feature = this.features.get(id)
    if (feature) {
      this.features.set(id, { ...feature, enabled: true })
      this.notifyListeners()
    }
  }

  disable(id: string): void {
    const feature = this.features.get(id)
    if (feature) {
      this.features.set(id, { ...feature, enabled: false })
      this.notifyListeners()
    }
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notifyListeners(): void {
    this.listeners.forEach((l) => l())
  }

  clear(): void {
    this.features.clear()
    this.notifyListeners()
  }
}

export const featureRegistry = new FeatureRegistryImpl()

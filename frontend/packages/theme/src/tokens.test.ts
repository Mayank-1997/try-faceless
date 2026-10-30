import { describe, it, expect } from 'vitest'
import { describe as describeTokens } from '../tokens'

describe('theme tokens', () => {
  it('should export color tokens', () => {
    expect(describeTokens.colors).toBeDefined()
  })

  it('should export spacing tokens', () => {
    expect(describeTokens.spacing).toBeDefined()
  })

  it('should export typography tokens', () => {
    expect(describeTokens.typography).toBeDefined()
  })

  it('should export shadow tokens', () => {
    expect(describeTokens.shadows).toBeDefined()
  })

  it('should export animation tokens', () => {
    expect(describeTokens.animations).toBeDefined()
  })

  it('should export breakpoint tokens', () => {
    expect(describeTokens.breakpoints).toBeDefined()
  })

  it('should export zIndex tokens', () => {
    expect(describeTokens.zIndex).toBeDefined()
  })
})

import { describe, it, expect, beforeEach } from 'vitest'
import { commandRegistry } from '../command-palette'
import type { CommandPaletteItem } from '@ai-video-studio/shared-types'

describe('CommandRegistry', () => {
  beforeEach(() => {
    commandRegistry.clear()
  })

  it('should register a command', () => {
    const cmd: CommandPaletteItem = {
      id: 'test-cmd',
      label: 'Test Command',
      action: () => {},
    }
    commandRegistry.register(cmd)
    expect(commandRegistry.getAll()).toHaveLength(1)
  })

  it('should unregister a command', () => {
    const cmd: CommandPaletteItem = {
      id: 'test-cmd',
      label: 'Test Command',
      action: () => {},
    }
    commandRegistry.register(cmd)
    commandRegistry.unregister('test-cmd')
    expect(commandRegistry.getAll()).toHaveLength(0)
  })

  it('should search commands by label', () => {
    commandRegistry.register({ id: '1', label: 'Open Settings', action: () => {} })
    commandRegistry.register({ id: '2', label: 'Delete User', action: () => {} })
    const results = commandRegistry.search('settings')
    expect(results).toHaveLength(1)
    expect(results[0].id).toBe('1')
  })

  it('should search commands by keywords', () => {
    commandRegistry.register({
      id: '1',
      label: 'Open',
      keywords: ['settings', 'preferences'],
      action: () => {},
    })
    const results = commandRegistry.search('preferences')
    expect(results).toHaveLength(1)
  })

  it('should search commands by category', () => {
    commandRegistry.register({
      id: '1',
      label: 'Export',
      category: 'Data',
      action: () => {},
    })
    const results = commandRegistry.search('data')
    expect(results).toHaveLength(1)
  })

  it('should sort by priority', () => {
    commandRegistry.register({ id: '1', label: 'B', priority: 2, action: () => {} })
    commandRegistry.register({ id: '2', label: 'A', priority: 1, action: () => {} })
    const results = commandRegistry.search('')
    expect(results[0].id).toBe('2')
  })
})

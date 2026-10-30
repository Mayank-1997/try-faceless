"use client"
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Search, Command } from '@ai-video-studio/icons'
import type { CommandPaletteItem } from '@ai-video-studio/shared-types'

class CommandRegistryImpl {
  private commands = new Map<string, CommandPaletteItem>()
  private listeners = new Set<() => void>()

  register(command: CommandPaletteItem): void {
    this.commands.set(command.id, command)
    this.notifyListeners()
  }

  unregister(id: string): void {
    this.commands.delete(id)
    this.notifyListeners()
  }

  getAll(): CommandPaletteItem[] {
    return Array.from(this.commands.values())
  }

  search(query: string): CommandPaletteItem[] {
    const lower = query.toLowerCase()
    return this.getAll()
      .filter((cmd) => {
        const matchesLabel = cmd.label.toLowerCase().includes(lower)
        const matchesKeywords = cmd.keywords?.some((k) => k.toLowerCase().includes(lower))
        const matchesCategory = cmd.category?.toLowerCase().includes(lower)
        return matchesLabel || matchesKeywords || matchesCategory
      })
      .sort((a, b) => (a.priority ?? 0) - (b.priority ?? 0))
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notifyListeners(): void {
    this.listeners.forEach((l) => l())
  }

  clear(): void {
    this.commands.clear()
    this.notifyListeners()
  }
}

export const commandRegistry = new CommandRegistryImpl()

export function useCommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const commands = useMemo(() => {
    return query ? commandRegistry.search(query) : commandRegistry.getAll()
  }, [query, open])

  const toggle = useCallback(() => {
    setOpen((v) => !v)
    setQuery('')
    setSelectedIndex(0)
  }, [])

  const close = useCallback(() => {
    setOpen(false)
    setQuery('')
    setSelectedIndex(0)
  }, [])

  const execute = useCallback(
    (command: CommandPaletteItem) => {
      command.action()
      close()
    },
    [close]
  )

  useEffect(() => {
    if (!open) return

    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        close()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((i) => Math.min(i + 1, commands.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && commands[selectedIndex]) {
        e.preventDefault()
        execute(commands[selectedIndex])
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, commands, selectedIndex, close, execute])

  useEffect(() => {
    const globalHandler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        toggle()
      }
    }
    document.addEventListener('keydown', globalHandler)
    return () => document.removeEventListener('keydown', globalHandler)
  }, [toggle])

  return {
    open,
    query,
    commands,
    selectedIndex,
    setQuery,
    setSelectedIndex,
    toggle,
    close,
    execute,
  }
}

export function CommandPalette() {
  const palette = useCommandPalette()

  if (!palette.open) return null

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={palette.close} />
      <div className="relative z-10 w-full max-w-xl rounded-lg border border-[var(--border-default)] bg-[var(--bg-modal)] shadow-[var(--shadow-lg)]">
        <div className="flex items-center gap-3 border-b border-[var(--border-default)] p-4">
          <Search className="h-4 w-4 text-[var(--fg-muted)]" />
          <input
            autoFocus
            type="text"
            placeholder="Type a command..."
            value={palette.query}
            onChange={(e) => {
              palette.setQuery(e.target.value)
              palette.setSelectedIndex(0)
            }}
            className="flex-1 bg-transparent text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] focus:outline-none"
          />
          <kbd className="rounded border border-[var(--border-default)] px-1.5 py-0.5 text-xs text-[var(--fg-muted)]">
            ESC
          </kbd>
        </div>
        <div className="max-h-[300px] overflow-y-auto p-2">
          {palette.commands.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <Command className="mb-2 h-8 w-8 text-[var(--fg-subtle)]" />
              <p className="text-sm text-[var(--fg-muted)]">No commands found</p>
            </div>
          ) : (
            palette.commands.map((cmd, i) => (
              <button
                key={cmd.id}
                onClick={() => palette.execute(cmd)}
                onMouseEnter={() => palette.setSelectedIndex(i)}
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  i === palette.selectedIndex
                    ? 'bg-[var(--bg-surface-hover)] text-[var(--fg-default)]'
                    : 'text-[var(--fg-default)]'
                }`}
              >
                {cmd.icon && <cmd.icon className="h-4 w-4 text-[var(--fg-muted)]" />}
                <span className="flex-1">{cmd.label}</span>
                {cmd.category && (
                  <span className="text-xs text-[var(--fg-subtle)]">{cmd.category}</span>
                )}
                {cmd.shortcut && (
                  <kbd className="rounded border border-[var(--border-default)] px-1.5 py-0.5 text-xs text-[var(--fg-muted)]">
                    {cmd.shortcut}
                  </kbd>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

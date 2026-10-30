'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Bell, Sun, Moon, Menu, LogOut } from '@ai-video-studio/icons'
import { useAuthStore, useTheme } from '@ai-video-studio/platform-kernel'
import { Avatar, Button } from '@ai-video-studio/design-system'

interface TopNavProps {
  onOpenSearch: () => void
  onToggleSidebar: () => void
}

export function TopNav({ onOpenSearch, onToggleSidebar }: TopNavProps) {
  const user = useAuthStore((s) => s.user)
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const { theme, toggleTheme } = useTheme()
  const [notifOpen, setNotifOpen] = useState(false)
  const router = useRouter()

  const handleLogout = useCallback(() => {
    clearAuth()
    router.push('/login')
  }, [clearAuth, router])

  const handleToggleTheme = useCallback(() => {
    toggleTheme()
  }, [toggleTheme])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        onOpenSearch()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onOpenSearch])

  return (
    <header className="flex h-14 items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="rounded-md p-1.5 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)]"
        >
          <Menu className="h-5 w-5" />
        </button>

        <button
          onClick={onOpenSearch}
          className="flex items-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--bg-base)] px-3 py-1.5 text-sm text-[var(--fg-muted)] hover:border-[var(--brand-default)] hover:text-[var(--fg-default)]"
        >
          <Search className="h-4 w-4" />
          <span>Search...</span>
          <kbd className="ml-8 rounded border border-[var(--border-default)] px-1.5 py-0.5 text-xs">
            ⌘K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={handleToggleTheme}>
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setNotifOpen(!notifOpen)}
          >
            <Bell className="h-4 w-4" />
          </Button>
          {notifOpen && (
            <div className="absolute right-0 top-full mt-2 w-80 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-lg">
              <div className="border-b border-[var(--border-default)] p-3 text-sm font-medium">
                Notifications
              </div>
              <div className="p-3 text-sm text-[var(--fg-muted)]">
                No new notifications
              </div>
            </div>
          )}
        </div>

        {user && (
          <div className="flex items-center gap-2">
            <Avatar
              src={user.profile_image_url ?? undefined}
              alt={user.full_name}
              fallback={user.full_name}
              size="sm"
            />
            <div className="hidden text-sm md:block">
              <div className="font-medium text-[var(--fg-default)]">{user.full_name}</div>
              <div className="text-xs text-[var(--fg-muted)]">{user.email}</div>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </header>
  )
}

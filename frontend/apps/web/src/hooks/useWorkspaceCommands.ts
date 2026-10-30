'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { commandRegistry } from '@ai-video-studio/platform-kernel'
import {
  LayoutDashboard,
  FolderKanban,
  Plus,
  Settings,
  LogOut,
  Sun,
  Moon,
} from '@ai-video-studio/icons'
import { useAuthStore, useTheme } from '@ai-video-studio/platform-kernel'

export function useWorkspaceCommands() {
  const router = useRouter()
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    const commands = [
      {
        id: 'nav-dashboard',
        label: 'Go to Dashboard',
        category: 'Navigation',
        icon: LayoutDashboard,
        action: () => router.push('/dashboard'),
      },
      {
        id: 'nav-projects',
        label: 'Go to Projects',
        category: 'Navigation',
        icon: FolderKanban,
        action: () => router.push('/projects'),
      },
      {
        id: 'nav-new-project',
        label: 'Create New Project',
        category: 'Actions',
        icon: Plus,
        action: () => router.push('/projects/new'),
      },
      {
        id: 'nav-settings',
        label: 'Go to Settings',
        category: 'Navigation',
        icon: Settings,
        action: () => router.push('/settings'),
      },
      {
        id: 'toggle-theme',
        label: 'Toggle Theme',
        category: 'Appearance',
        icon: theme === 'dark' ? Sun : Moon,
        action: () => toggleTheme(),
      },
      {
        id: 'logout',
        label: 'Sign Out',
        category: 'Account',
        icon: LogOut,
        action: () => {
          clearAuth()
          router.push('/login')
        },
      },
    ]

    commands.forEach((cmd) => commandRegistry.register(cmd))

    return () => {
      commands.forEach((cmd) => commandRegistry.unregister(cmd.id))
    }
  }, [router, clearAuth, theme, toggleTheme])
}

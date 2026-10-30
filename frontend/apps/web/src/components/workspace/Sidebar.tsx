'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  FolderKanban,
  Plus,
  Settings,
  HelpCircle,
  Video,
  ChevronLeft,
} from '@ai-video-studio/icons'
import { cn } from '@ai-video-studio/design-system'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Projects', href: '/projects', icon: FolderKanban },
]

const bottomItems = [
  { label: 'Settings', href: '/settings', icon: Settings },
  { label: 'Help', href: '/help', icon: HelpCircle },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-[var(--border-default)] bg-[var(--bg-surface)] transition-all duration-200',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-[var(--border-default)] px-4">
        <Video className="h-6 w-6 shrink-0 text-[var(--brand-default)]" />
        {!collapsed && (
          <span className="text-sm font-semibold text-[var(--fg-default)]">
            AI Video Studio
          </span>
        )}
      </div>

      {/* New Project button */}
      <div className="p-3">
        <Link
          href="/projects/new"
          className={cn(
            'flex items-center gap-2 rounded-md bg-[var(--brand-default)] px-3 py-2 text-sm font-medium text-[var(--fg-on-brand)] hover:bg-[var(--brand-hover)]',
            collapsed && 'justify-center px-2'
          )}
        >
          <Plus className="h-4 w-4 shrink-0" />
          {!collapsed && 'New Project'}
        </Link>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 px-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                collapsed && 'justify-center px-2',
                isActive
                  ? 'bg-[var(--bg-surface-hover)] text-[var(--fg-default)] font-medium'
                  : 'text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && item.label}
            </Link>
          )
        })}
      </nav>

      {/* Bottom items */}
      <div className="space-y-1 border-t border-[var(--border-default)] p-3">
        {bottomItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                collapsed && 'justify-center px-2',
                isActive
                  ? 'bg-[var(--bg-surface-hover)] text-[var(--fg-default)] font-medium'
                  : 'text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && item.label}
            </Link>
          )
        })}

        {/* Collapse toggle */}
        <button
          onClick={onToggle}
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]',
            collapsed && 'justify-center px-2'
          )}
        >
          <ChevronLeft className={cn('h-4 w-4 shrink-0 transition-transform', collapsed && 'rotate-180')} />
          {!collapsed && 'Collapse'}
        </button>
      </div>
    </aside>
  )
}

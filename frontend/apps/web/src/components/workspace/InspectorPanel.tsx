'use client'

import { X } from '@ai-video-studio/icons'
import { cn } from '@ai-video-studio/design-system'
import type { ReactNode } from 'react'

interface InspectorPanelProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
}

export function InspectorPanel({ open, onClose, title, children }: InspectorPanelProps) {
  return (
    <aside
      className={cn(
        'flex flex-col border-l border-[var(--border-default)] bg-[var(--bg-surface)] transition-all duration-200',
        open ? 'w-80' : 'w-0 overflow-hidden'
      )}
    >
      {open && (
        <>
          <div className="flex h-14 items-center justify-between border-b border-[var(--border-default)] px-4">
            <h3 className="text-sm font-semibold text-[var(--fg-default)]">{title ?? 'Inspector'}</h3>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">{children}</div>
        </>
      )}
    </aside>
  )
}

"use client"

import React from 'react'
import { useEffect } from 'react'
import { X } from '@ai-video-studio/icons'
import { cn } from '../lib/cn'

export interface DrawerProps {
  open: boolean
  onClose: () => void
  side?: 'left' | 'right' | 'top' | 'bottom'
  title?: string
  children?: React.ReactNode
  className?: string
}

const sideClasses = {
  left: 'left-0 top-0 h-full w-80 max-w-full',
  right: 'right-0 top-0 h-full w-80 max-w-full',
  top: 'top-0 left-0 w-full max-h-[80vh]',
  bottom: 'bottom-0 left-0 w-full max-h-[80vh]',
}

export function Drawer({ open, onClose, side = 'right', title, children, className }: DrawerProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[var(--z-modal)]">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'absolute border-[var(--border-default)] bg-[var(--bg-modal)] shadow-[var(--shadow-lg)]',
          sideClasses[side],
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--border-default)] p-4">
            <h2 className="text-base font-semibold text-[var(--fg-default)]">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]"
              aria-label="Close drawer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}

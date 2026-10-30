"use client"

import React from 'react'
import { useEffect } from 'react'
import { X } from '@ai-video-studio/icons'
import { cn } from '../lib/cn'

export interface DialogProps {
  open: boolean
  onClose: () => void
  title?: string
  description?: string
  children?: React.ReactNode
  className?: string
}

export function Dialog({ open, onClose, title, description, children, className }: DialogProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'dialog-title' : undefined}
        className={cn(
          'relative z-10 w-full max-w-lg rounded-lg border border-[var(--border-default)] bg-[var(--bg-modal)] p-6 shadow-[var(--shadow-lg)]',
          className
        )}
      >
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 id="dialog-title" className="text-lg font-semibold text-[var(--fg-default)]">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]"
              aria-label="Close dialog"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        {description && (
          <p className="mb-4 text-sm text-[var(--fg-muted)]">{description}</p>
        )}
        {children}
      </div>
    </div>
  )
}

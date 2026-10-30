"use client"
import React, { useState, useCallback } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from '@ai-video-studio/icons'
import { cn } from '../lib/cn'

export type ToastVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

export interface Toast {
  id: string
  title: string
  description?: string
  variant?: ToastVariant
  duration?: number
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

const variantConfig = {
  default: { icon: null, className: '' },
  success: { icon: CheckCircle, className: 'text-[var(--success)]' },
  warning: { icon: AlertTriangle, className: 'text-[var(--warning)]' },
  error: { icon: AlertCircle, className: 'text-[var(--error)]' },
  info: { icon: Info, className: 'text-[var(--info)]' },
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).slice(2)
      const newToast: Toast = { id, duration: 5000, variant: 'default', ...toast }
      setToasts((prev) => [...prev, newToast])
      if (newToast.duration && newToast.duration > 0) {
        setTimeout(() => removeToast(id), newToast.duration)
      }
    },
    [removeToast]
  )

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-0 right-0 z-[var(--z-toast)] flex flex-col gap-2 p-4 sm:max-w-sm">
        {toasts.map((toast) => {
          const config = variantConfig[toast.variant ?? 'default']
          const Icon = config.icon
          return (
            <div
              key={toast.id}
              className={cn(
                'flex items-start gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] p-4 shadow-[var(--shadow-lg)]'
              )}
              role="alert"
            >
              {Icon && <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', config.className)} />}
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--fg-default)]">{toast.title}</p>
                {toast.description && (
                  <p className="mt-1 text-sm text-[var(--fg-muted)]">{toast.description}</p>
                )}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--fg-default)]"
                aria-label="Dismiss toast"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = React.useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

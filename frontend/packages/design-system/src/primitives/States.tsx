import React from 'react'
import { AlertCircle, Inbox, Loader2 } from '@ai-video-studio/icons'
import { cn } from '../lib/cn'

export function EmptyState({
  icon,
  title = 'Nothing here yet',
  description,
  action,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }> | React.ReactElement
  title?: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  const iconElement = icon
    ? React.isValidElement(icon)
      ? icon
      : React.createElement(icon as React.ComponentType<{ className?: string }>, { className: 'mb-4 h-12 w-12 text-[var(--fg-subtle)]' })
    : <Inbox className="mb-4 h-12 w-12 text-[var(--fg-subtle)]" />
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      {iconElement}
      <h3 className="mb-2 text-lg font-semibold text-[var(--fg-default)]">{title}</h3>
      {description && <p className="mb-6 max-w-sm text-sm text-[var(--fg-muted)]">{description}</p>}
      {action}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  action,
  className,
}: {
  title?: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      <AlertCircle className="mb-4 h-12 w-12 text-[var(--error)]" />
      <h3 className="mb-2 text-lg font-semibold text-[var(--fg-default)]">{title}</h3>
      {description && <p className="mb-6 max-w-sm text-sm text-[var(--fg-muted)]">{description}</p>}
      {action}
    </div>
  )
}

export function LoadingState({
  label = 'Loading...',
  className,
}: {
  label?: string
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      <Loader2 className="mb-4 h-8 w-8 animate-spin text-[var(--brand-default)]" />
      <p className="text-sm text-[var(--fg-muted)]">{label}</p>
    </div>
  )
}

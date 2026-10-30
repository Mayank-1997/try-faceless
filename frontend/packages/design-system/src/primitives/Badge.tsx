import React from 'react'
import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../lib/cn'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-[var(--brand-subtle)] text-[var(--brand-default)]',
        secondary: 'border-transparent bg-[var(--bg-surface-hover)] text-[var(--fg-default)]',
        success: 'border-transparent bg-[var(--success-bg)] text-[var(--success)]',
        warning: 'border-transparent bg-[var(--warning-bg)] text-[var(--warning)]',
        error: 'border-transparent bg-[var(--error-bg)] text-[var(--error)]',
        info: 'border-transparent bg-[var(--info-bg)] text-[var(--info)]',
        outline: 'border-[var(--border-default)] text-[var(--fg-default)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
  )
)
Badge.displayName = 'Badge'

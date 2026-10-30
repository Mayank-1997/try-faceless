import React from 'react'
import { forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../lib/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-[var(--brand-default)] text-[var(--fg-on-brand)] hover:bg-[var(--brand-hover)] active:bg-[var(--brand-active)]',
        secondary: 'bg-[var(--bg-surface-hover)] text-[var(--fg-default)] hover:bg-[var(--bg-surface-active)]',
        outline: 'border border-[var(--border-default)] bg-transparent text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]',
        ghost: 'bg-transparent text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]',
        destructive: 'bg-[var(--error)] text-white hover:bg-[var(--error)]/90',
        link: 'text-[var(--brand-default)] underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

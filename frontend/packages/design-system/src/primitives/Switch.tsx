import React from 'react'
import { forwardRef } from 'react'
import { cn } from '../lib/cn'

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
}

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked, onCheckedChange, ...props }, ref) => (
    <label className={cn('relative inline-flex cursor-pointer items-center', className)}>
      <input
        ref={ref}
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        {...props}
      />
      <div className="h-6 w-11 rounded-full bg-[var(--bg-surface-active)] peer-checked:bg-[var(--brand-default)] peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--focus-ring)] transition-colors" />
      <div className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-5" />
    </label>
  )
)
Switch.displayName = 'Switch'

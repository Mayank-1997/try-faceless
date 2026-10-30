import React from 'react'
import { forwardRef } from 'react'
import { Check } from '@ai-video-studio/icons'
import { cn } from '../lib/cn'

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, ...props }, ref) => (
    <label className={cn('inline-flex cursor-pointer items-center', className)}>
      <input
        ref={ref}
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        {...props}
      />
      <div className="flex h-4 w-4 items-center justify-center rounded border border-[var(--border-default)] bg-[var(--bg-elevated)] peer-checked:border-[var(--brand-default)] peer-checked:bg-[var(--brand-default)] peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--focus-ring)] transition-colors">
        {checked && <Check className="h-3 w-3 text-[var(--fg-on-brand)]" />}
      </div>
    </label>
  )
)
Checkbox.displayName = 'Checkbox'

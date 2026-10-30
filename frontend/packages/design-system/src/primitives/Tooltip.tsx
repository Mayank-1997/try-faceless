import React from 'react'
import { forwardRef } from 'react'
import { cn } from '../lib/cn'

export interface TooltipProps {
  content: string
  children: React.ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
}

const sideClasses = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
}

export const Tooltip = forwardRef<HTMLDivElement, TooltipProps>(
  ({ content, children, side = 'top' }, ref) => (
    <div ref={ref} className="group relative inline-flex">
      {children}
      <div
        className={cn(
          'pointer-events-none absolute z-[var(--z-tooltip)] whitespace-nowrap rounded-md bg-black/90 px-2.5 py-1.5 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100',
          sideClasses[side]
        )}
        role="tooltip"
      >
        {content}
      </div>
    </div>
  )
)
Tooltip.displayName = 'Tooltip'

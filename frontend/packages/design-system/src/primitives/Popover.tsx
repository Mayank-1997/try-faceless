"use client"

import React from 'react'
import { useState } from 'react'
import { cn } from '../lib/cn'

export interface PopoverProps {
  trigger: React.ReactNode
  children: React.ReactNode
  align?: 'start' | 'center' | 'end'
  className?: string
}

const alignClasses = {
  start: 'left-0',
  center: 'left-1/2 -translate-x-1/2',
  end: 'right-0',
}

export function Popover({ trigger, children, align = 'center', className }: PopoverProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative inline-flex">
      <div onClick={() => setOpen((v) => !v)}>{trigger}</div>
      {open && (
        <>
          <div className="fixed inset-0 z-0" onClick={() => setOpen(false)} aria-hidden="true" />
          <div
            className={cn(
              'absolute top-full z-10 mt-2 min-w-[200px] rounded-md border border-[var(--border-default)] bg-[var(--bg-popover)] p-4 shadow-[var(--shadow-md)]',
              alignClasses[align],
              className
            )}
          >
            {children}
          </div>
        </>
      )}
    </div>
  )
}

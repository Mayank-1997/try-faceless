"use client"
import React, { useState } from 'react'
import { cn } from '../lib/cn'

export interface TabsProps {
  defaultValue?: string
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  className?: string
}

export interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {}
export interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}
export interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

const TabsContext = React.createContext<{ value: string; setValue: (v: string) => void } | null>(null)

export function Tabs({ defaultValue = '', value: controlled, onValueChange, children, className }: TabsProps) {
  const [uncontrolled, setUncontrolled] = useState(defaultValue)
  const value = controlled ?? uncontrolled
  const setValue = (v: string) => {
    if (controlled === undefined) setUncontrolled(v)
    onValueChange?.(v)
  }

  return (
    <TabsContext.Provider value={{ value, setValue }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

export function TabsList({ className, ...props }: TabsListProps) {
  return (
    <div
      className={cn(
        'inline-flex h-10 items-center justify-center gap-1 rounded-md bg-[var(--bg-surface)] p-1',
        className
      )}
      {...props}
    />
  )
}

export function TabsTrigger({ className, value, ...props }: TabsTriggerProps) {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error('TabsTrigger must be used within Tabs')
  const isActive = ctx.value === value

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]',
        isActive
          ? 'bg-[var(--bg-elevated)] text-[var(--fg-default)] shadow-[var(--shadow-sm)]'
          : 'text-[var(--fg-muted)] hover:text-[var(--fg-default)]',
        className
      )}
      onClick={() => ctx.setValue(value)}
      {...props}
    />
  )
}

export function TabsContent({ className, value, ...props }: TabsContentProps) {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error('TabsContent must be used within Tabs')
  if (ctx.value !== value) return null

  return (
    <div className={cn('mt-2 focus-visible:outline-none', className)} {...props} />
  )
}

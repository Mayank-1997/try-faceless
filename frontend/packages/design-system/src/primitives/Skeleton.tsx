import React from 'react'
import { cn } from '../lib/cn'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-[var(--bg-surface-hover)]', className)}
      {...props}
    />
  )
}

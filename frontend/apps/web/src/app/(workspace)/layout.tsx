'use client'

import { useAuthStore } from '@ai-video-studio/platform-kernel'
import { useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'
import { WorkspaceShell } from '@/components/workspace/WorkspaceShell'
import { useWorkspaceCommands } from '@/hooks/useWorkspaceCommands'

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)
  const router = useRouter()

  useWorkspaceCommands()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login')
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-sm text-[var(--fg-muted)]">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return <WorkspaceShell>{children}</WorkspaceShell>
}

'use client'

import { useState, useEffect } from 'react'
import { Activity, Wifi } from '@ai-video-studio/icons'
import { realtimeProvider } from '@ai-video-studio/platform-kernel'

interface StatusBarProps {
  projectName?: string
  workflowStep?: string
}

export function StatusBar({ projectName, workflowStep }: StatusBarProps) {
  const [isConnected, setIsConnected] = useState(realtimeProvider.isConnected())

  useEffect(() => {
    const unsub = realtimeProvider.on('realtime:connected', () => setIsConnected(true))
    const unsub2 = realtimeProvider.on('realtime:disconnected', () => setIsConnected(false))
    return () => {
      unsub()
      unsub2()
    }
  }, [])

  return (
    <footer className="flex h-7 items-center justify-between border-t border-[var(--border-default)] bg-[var(--bg-surface)] px-4 text-xs text-[var(--fg-muted)]">
      <div className="flex items-center gap-3">
        {projectName && (
          <span className="font-medium text-[var(--fg-default)]">{projectName}</span>
        )}
        {workflowStep && (
          <>
            <span>—</span>
            <span>{workflowStep}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <Activity className="h-3 w-3" />
          <span>Ready</span>
        </div>
        <div className="flex items-center gap-1">
          <Wifi className="h-3 w-3" />
          <span className={isConnected ? 'text-[var(--status-success)]' : 'text-[var(--status-error)]'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </footer>
  )
}

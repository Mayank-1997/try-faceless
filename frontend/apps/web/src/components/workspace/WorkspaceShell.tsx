'use client'

import { useState, useCallback, type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'
import { InspectorPanel } from './InspectorPanel'
import { StatusBar } from './StatusBar'
import { CommandPalette, useCommandPalette } from '@ai-video-studio/platform-kernel'

interface WorkspaceShellProps {
  children: ReactNode
  inspectorContent?: ReactNode
  inspectorTitle?: string
  projectName?: string
  workflowStep?: string
}

export function WorkspaceShell({
  children,
  inspectorContent,
  inspectorTitle,
  projectName,
  workflowStep,
}: WorkspaceShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [inspectorOpen, setInspectorOpen] = useState(!!inspectorContent)
  const palette = useCommandPalette()

  const toggleSidebar = useCallback(() => setSidebarCollapsed((v) => !v), [])

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />

        <div className="flex flex-1 flex-col overflow-hidden">
          <TopNav onOpenSearch={palette.toggle} onToggleSidebar={toggleSidebar} />
          <main className="flex-1 overflow-y-auto bg-[var(--bg-base)]">{children}</main>
          <StatusBar projectName={projectName} workflowStep={workflowStep} />
        </div>

        {inspectorContent && (
          <InspectorPanel
            open={inspectorOpen}
            onClose={() => setInspectorOpen(false)}
            title={inspectorTitle}
          >
            {inspectorContent}
          </InspectorPanel>
        )}
      </div>

      <CommandPalette />
    </div>
  )
}

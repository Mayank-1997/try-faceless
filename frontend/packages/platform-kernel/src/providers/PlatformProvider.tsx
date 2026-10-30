"use client"
import { useEffect, type ReactNode } from 'react'
import { type EnvironmentConfig, type PluginDefinition } from '@ai-video-studio/shared-types'
import { initSDK } from '@ai-video-studio/platform-sdk'
import { ErrorBoundary } from './ErrorBoundary'
import { ThemeProvider } from './ThemeProvider'
import { QueryProvider } from './QueryProvider'
import { ToastProvider } from '@ai-video-studio/design-system'
import { useAuthStore, useEnvStore } from '../stores/auth-store'
import { pluginManager } from '../plugin-manager'
import { CommandPalette } from '../command-palette'
import { realtimeProvider } from '../realtime'

export interface PlatformProviderProps {
  config: EnvironmentConfig
  plugins?: PluginDefinition[]
  children: ReactNode
}

export function PlatformProvider({ config, plugins = [], children }: PlatformProviderProps) {
  const setConfig = useEnvStore((s) => s.setConfig)
  const accessToken = useAuthStore((s) => s.accessToken)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const setUser = useAuthStore((s) => s.setUser)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const setLoading = useAuthStore((s) => s.setLoading)

  useEffect(() => {
    setConfig(config)
  }, [config, setConfig])

  useEffect(() => {
    initSDK({
      baseURL: config.apiBaseUrl,
      getAccessToken: () => useAuthStore.getState().accessToken,
      getRefreshToken: () => useAuthStore.getState().refreshToken,
      setTokens: (access, refresh) => setTokens(access, refresh),
      clearTokens: () => clearAuth(),
      onUnauthorized: () => {
        clearAuth()
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      },
    })

    pluginManager.setContext({
      config,
      realtime: realtimeProvider,
    })

    for (const plugin of plugins) {
      pluginManager.register(plugin)
    }

    setLoading(false)

    return () => {
      pluginManager.clear()
    }
  }, [config, plugins, setTokens, clearAuth, setLoading])

  useEffect(() => {
    if (config.wsUrl && accessToken) {
      realtimeProvider.connect(config.wsUrl, accessToken)
    }
    return () => {
      realtimeProvider.disconnect()
    }
  }, [config.wsUrl, accessToken])

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryProvider>
          <ToastProvider>
            {children}
            <CommandPalette />
          </ToastProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

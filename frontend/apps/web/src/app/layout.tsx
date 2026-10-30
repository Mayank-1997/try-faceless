import type { Metadata } from 'next'
import { PlatformProvider } from '@ai-video-studio/platform-kernel'
import type { EnvironmentConfig } from '@ai-video-studio/shared-types'
import { lightTheme, darkTheme, type ThemeVariables } from '@ai-video-studio/theme'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Video Studio',
  description: 'AI-powered video automation platform',
}

const envConfig: EnvironmentConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL,
  appName: 'AI Video Studio',
  appVersion: process.env.NEXT_PUBLIC_APP_VERSION ?? '0.0.0',
  environment: (process.env.NEXT_PUBLIC_ENV as 'development' | 'staging' | 'production') ?? 'development',
}

function themeToCss(vars: ThemeVariables): string {
  return Object.entries(vars).map(([k, v]) => `${k}: ${v};`).join(' ')
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <style dangerouslySetInnerHTML={{ __html: `:root { ${themeToCss(lightTheme)} } .dark { ${themeToCss(darkTheme)} }` }} />
      </head>
      <body>
        <PlatformProvider config={envConfig}>{children}</PlatformProvider>
      </body>
    </html>
  )
}

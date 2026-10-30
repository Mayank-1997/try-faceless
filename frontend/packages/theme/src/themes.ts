// CSS variable-based theme definitions for dark/light mode.
// These are injected at runtime by the ThemeProvider.

export interface ThemeVariables {
  // Backgrounds
  '--bg-background': string
  '--bg-surface': string
  '--bg-surface-hover': string
  '--bg-surface-active': string
  '--bg-elevated': string
  '--bg-popover': string
  '--bg-modal': string

  // Foregrounds
  '--fg-default': string
  '--fg-muted': string
  '--fg-subtle': string
  '--fg-on-brand': string
  '--fg-on-accent': string

  // Borders
  '--border-default': string
  '--border-subtle': string
  '--border-strong': string

  // Brand
  '--brand-default': string
  '--brand-hover': string
  '--brand-active': string
  '--brand-subtle': string

  // Accent
  '--accent-default': string
  '--accent-hover': string

  // Semantic
  '--success': string
  '--success-bg': string
  '--warning': string
  '--warning-bg': string
  '--error': string
  '--error-bg': string
  '--info': string
  '--info-bg': string

  // Focus ring
  '--focus-ring': string

  // Shadows
  '--shadow-sm': string
  '--shadow-md': string
  '--shadow-lg': string
}

export const lightTheme: ThemeVariables = {
  '--bg-background': '#ffffff',
  '--bg-surface': '#f9fafb',
  '--bg-surface-hover': '#f3f4f6',
  '--bg-surface-active': '#e5e7eb',
  '--bg-elevated': '#ffffff',
  '--bg-popover': '#ffffff',
  '--bg-modal': '#ffffff',

  '--fg-default': '#111827',
  '--fg-muted': '#6b7280',
  '--fg-subtle': '#9ca3af',
  '--fg-on-brand': '#ffffff',
  '--fg-on-accent': '#ffffff',

  '--border-default': '#e5e7eb',
  '--border-subtle': '#f3f4f6',
  '--border-strong': '#d1d5db',

  '--brand-default': '#6366f1',
  '--brand-hover': '#4f46e5',
  '--brand-active': '#4338ca',
  '--brand-subtle': '#eef2ff',

  '--accent-default': '#d946ef',
  '--accent-hover': '#c026d3',

  '--success': '#22c55e',
  '--success-bg': '#f0fdf4',
  '--warning': '#f59e0b',
  '--warning-bg': '#fffbeb',
  '--error': '#ef4444',
  '--error-bg': '#fef2f2',
  '--info': '#3b82f6',
  '--info-bg': '#eff6ff',

  '--focus-ring': '0 0 0 2px #ffffff, 0 0 0 4px #6366f1',

  '--shadow-sm': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
}

export const darkTheme: ThemeVariables = {
  '--bg-background': '#0a0a0a',
  '--bg-surface': '#141414',
  '--bg-surface-hover': '#1c1c1c',
  '--bg-surface-active': '#262626',
  '--bg-elevated': '#1a1a1a',
  '--bg-popover': '#1a1a1a',
  '--bg-modal': '#1a1a1a',

  '--fg-default': '#fafafa',
  '--fg-muted': '#a3a3a3',
  '--fg-subtle': '#737373',
  '--fg-on-brand': '#ffffff',
  '--fg-on-accent': '#ffffff',

  '--border-default': '#262626',
  '--border-subtle': '#1c1c1c',
  '--border-strong': '#404040',

  '--brand-default': '#818cf8',
  '--brand-hover': '#6366f1',
  '--brand-active': '#4f46e5',
  '--brand-subtle': '#1e1b4b',

  '--accent-default': '#e879f9',
  '--accent-hover': '#d946ef',

  '--success': '#4ade80',
  '--success-bg': '#052e16',
  '--warning': '#fbbf24',
  '--warning-bg': '#422006',
  '--error': '#f87171',
  '--error-bg': '#450a0a',
  '--info': '#60a5fa',
  '--info-bg': '#0c1b2e',

  '--focus-ring': '0 0 0 2px #0a0a0a, 0 0 0 4px #818cf8',

  '--shadow-sm': '0 1px 3px 0 rgb(0 0 0 / 0.3), 0 1px 2px -1px rgb(0 0 0 / 0.3)',
  '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.4)',
  '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.5)',
}

export function applyThemeVariables(
  target: HTMLElement,
  variables: ThemeVariables
): void {
  for (const [key, value] of Object.entries(variables)) {
    target.style.setProperty(key, value)
  }
}

export function getThemeVariables(mode: 'light' | 'dark'): ThemeVariables {
  return mode === 'dark' ? darkTheme : lightTheme
}

export function applyTheme(mode: 'light' | 'dark' | 'system'): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  let resolved: 'light' | 'dark' = mode
  if (mode === 'system') {
    resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  root.classList.toggle('dark', resolved === 'dark')
  applyThemeVariables(root, getThemeVariables(resolved))
}

"use client"
import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertCircle, RefreshCw } from '@ai-video-studio/icons'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.props.onError?.(error, errorInfo)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-8">
          <AlertCircle className="mb-4 h-12 w-12 text-[var(--error)]" />
          <h2 className="mb-2 text-lg font-semibold text-[var(--fg-default)]">
            Something went wrong
          </h2>
          <p className="mb-4 max-w-md text-center text-sm text-[var(--fg-muted)]">
            {this.state.error?.message ?? 'An unexpected error occurred. Please try again.'}
          </p>
          <button
            onClick={this.handleReset}
            className="inline-flex items-center gap-2 rounded-md bg-[var(--brand-default)] px-4 py-2 text-sm font-medium text-[var(--fg-on-brand)] hover:bg-[var(--brand-hover)]"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

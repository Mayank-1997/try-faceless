import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import type { ApiError } from '@ai-video-studio/shared-types'

export interface ApiClientConfig {
  baseURL: string
  timeout?: number
  getAccessToken?: () => string | null
  getRefreshToken?: () => string | null
  setTokens?: (access: string, refresh: string) => void
  clearTokens?: () => void
  onUnauthorized?: () => void
  onError?: (error: ApiError) => void
  onRetry?: (config: AxiosRequestConfig, attempt: number) => void
}

const MAX_RETRIES = 3
const RETRY_DELAY = 1000
const RETRYABLE_STATUS = [408, 429, 500, 502, 503, 504]

export class ApiClient {
  private instance: AxiosInstance
  private config: ApiClientConfig
  private isRefreshing = false
  private refreshPromise: Promise<string> | null = null

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 30000,
      ...config,
    }

    this.instance = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // Request interceptor — attach auth token
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.config.getAccessToken?.()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor — error handling, token refresh, retry
    this.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: number }

        // Token refresh on 401
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = 1
          if (this.isRefreshing) {
            return this.refreshPromise!.then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              return this.instance(originalRequest)
            })
          }

          return this.refreshToken(originalRequest)
        }

        // Retry for retryable status codes
        if (originalRequest && RETRYABLE_STATUS.includes(error.response?.status ?? 0)) {
          const retryCount = originalRequest._retry ?? 0
          if (retryCount < MAX_RETRIES) {
            originalRequest._retry = retryCount + 1
            this.config.onRetry?.(originalRequest, retryCount + 1)
            await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * Math.pow(2, retryCount)))
            return this.instance(originalRequest)
          }
        }

        // Map error
        const apiError = this.mapError(error)
        this.config.onError?.(apiError)

        if (error.response?.status === 401) {
          this.config.onUnauthorized?.()
        }

        return Promise.reject(apiError)
      }
    )
  }

  private async refreshToken(originalRequest: InternalAxiosRequestConfig): Promise<unknown> {
    this.isRefreshing = true
    const refreshToken = this.config.getRefreshToken?.()

    if (!refreshToken) {
      this.isRefreshing = false
      this.config.onUnauthorized?.()
      return Promise.reject(this.mapError({ response: { status: 401, data: { message: 'No refresh token' } } } as AxiosError))
    }

    this.refreshPromise = axios
      .post(`${this.config.baseURL}/auth/refresh`, { refresh_token: refreshToken })
      .then((res) => {
        const { access_token, refresh_token } = res.data
        this.config.setTokens?.(access_token, refresh_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return access_token
      })
      .catch((err) => {
        this.config.onUnauthorized?.()
        throw this.mapError(err)
      })
      .finally(() => {
        this.isRefreshing = false
        this.refreshPromise = null
      })

    const token = await this.refreshPromise
    return this.instance(originalRequest)
  }

  private mapError(error: AxiosError): ApiError {
    if (error.response) {
      const data = error.response.data as Record<string, unknown>
      const nestedError = data.error as Record<string, unknown> | undefined
      const detail = data.detail as string | Array<{ loc?: unknown[]; msg?: string }> | undefined
      const detailMessage = Array.isArray(detail)
        ? detail
            .map((d) => {
              const field = (d.loc ?? []).filter((p) => p !== 'body').join('.')
              const msg = (d.msg ?? '').replace(/^Value error, /, '')
              return field ? `${field}: ${msg}` : msg
            })
            .join('; ')
        : typeof detail === 'string'
          ? detail
          : undefined
      return {
        error: (nestedError?.code as string) ?? (data.error as string) ?? error.name ?? 'request_error',
        message: (nestedError?.message as string) ?? (data.message as string) ?? detailMessage ?? error.message ?? 'An error occurred',
        details: (nestedError?.details as Record<string, unknown>) ?? (data.details as Record<string, unknown> | undefined),
        status_code: error.response.status,
        correlation_id: data.correlation_id as string | undefined,
      }
    }
    if (error.request) {
      return {
        error: 'network_error',
        message: 'Network error — please check your connection',
        status_code: 0,
      }
    }
    return {
      error: 'unknown_error',
      message: error.message ?? 'An unknown error occurred',
      status_code: 0,
    }
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const res = await this.instance.get<T>(url, config)
    return res.data
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const res = await this.instance.post<T>(url, data, config)
    return res.data
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const res = await this.instance.put<T>(url, data, config)
    return res.data
  }

  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const res = await this.instance.patch<T>(url, data, config)
    return res.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const res = await this.instance.delete<T>(url, config)
    return res.data
  }

  get axiosInstance(): AxiosInstance {
    return this.instance
  }
}

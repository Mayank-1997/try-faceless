import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserResponse, EnvironmentConfig } from '@ai-video-studio/shared-types'

interface AuthState {
  user: UserResponse | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: UserResponse | null) => void
  setTokens: (access: string, refresh: string) => void
  clearAuth: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) =>
        set({ user, isAuthenticated: !!user }),

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      clearAuth: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
        }),

      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = !!state.user
          state.isLoading = false
        }
      },
    }
  )
)

interface EnvState {
  config: EnvironmentConfig | null
  setConfig: (config: EnvironmentConfig) => void
}

export const useEnvStore = create<EnvState>((set) => ({
  config: null,
  setConfig: (config) => set({ config }),
}))

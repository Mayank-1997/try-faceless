import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  AuthResponse,
  RegisterRequest,
  LoginRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  VerifyEmailRequest,
  ResendVerificationRequest,
  MessageResponse,
  ApiError,
} from '@ai-video-studio/shared-types'

// Query keys
export const authKeys = {
  all: ['auth'] as const,
  session: ['auth', 'session'] as const,
}

// Hooks
export function useLogin(
  options?: UseMutationOptions<AuthResponse, ApiError, LoginRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: LoginRequest) => getSDK().auth.login(data),
    onSuccess: (data) => {
      queryClient.setQueryData(authKeys.session, data.user)
    },
    ...options,
  })
}

export function useRegister(
  options?: UseMutationOptions<AuthResponse, ApiError, RegisterRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: RegisterRequest) => getSDK().auth.register(data),
    onSuccess: (data) => {
      queryClient.setQueryData(authKeys.session, data.user)
    },
    ...options,
  })
}

export function useLogout(
  options?: UseMutationOptions<MessageResponse, ApiError, void>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => getSDK().auth.logout(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: authKeys.all })
    },
    ...options,
  })
}

export function useForgotPassword(
  options?: UseMutationOptions<MessageResponse, ApiError, ForgotPasswordRequest>
) {
  return useMutation({
    mutationFn: (data: ForgotPasswordRequest) => getSDK().auth.forgotPassword(data),
    ...options,
  })
}

export function useResetPassword(
  options?: UseMutationOptions<MessageResponse, ApiError, ResetPasswordRequest>
) {
  return useMutation({
    mutationFn: (data: ResetPasswordRequest) => getSDK().auth.resetPassword(data),
    ...options,
  })
}

export function useVerifyEmail(
  options?: UseMutationOptions<MessageResponse, ApiError, VerifyEmailRequest>
) {
  return useMutation({
    mutationFn: (data: VerifyEmailRequest) => getSDK().auth.verifyEmail(data),
    ...options,
  })
}

export function useResendVerification(
  options?: UseMutationOptions<MessageResponse, ApiError, ResendVerificationRequest>
) {
  return useMutation({
    mutationFn: (data: ResendVerificationRequest) => getSDK().auth.resendVerification(data),
    ...options,
  })
}

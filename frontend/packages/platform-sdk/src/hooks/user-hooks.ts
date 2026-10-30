import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  UserResponse,
  UserListResponse,
  UserPreferencesResponse,
  UpdateProfileRequest,
  ChangePasswordRequest,
  UpdatePreferencesRequest,
  MessageResponse,
  ApiError,
} from '@ai-video-studio/shared-types'

export const userKeys = {
  all: ['users'] as const,
  me: ['users', 'me'] as const,
  preferences: ['users', 'me', 'preferences'] as const,
  list: ['users', 'list'] as const,
}

export function useCurrentUser(
  options?: UseQueryOptions<UserResponse, ApiError>
) {
  return useQuery({
    queryKey: userKeys.me,
    queryFn: () => getSDK().users.getCurrentUser(),
    ...options,
  })
}

export function useUpdateProfile(
  options?: UseMutationOptions<UserResponse, ApiError, UpdateProfileRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdateProfileRequest) => getSDK().users.updateProfile(data),
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.me, data)
    },
    ...options,
  })
}

export function useChangePassword(
  options?: UseMutationOptions<MessageResponse, ApiError, ChangePasswordRequest>
) {
  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => getSDK().users.changePassword(data),
    ...options,
  })
}

export function usePreferences(
  options?: UseQueryOptions<UserPreferencesResponse, ApiError>
) {
  return useQuery({
    queryKey: userKeys.preferences,
    queryFn: () => getSDK().users.getPreferences(),
    ...options,
  })
}

export function useUpdatePreferences(
  options?: UseMutationOptions<UserPreferencesResponse, ApiError, UpdatePreferencesRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdatePreferencesRequest) => getSDK().users.updatePreferences(data),
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.preferences, data)
    },
    ...options,
  })
}

export function useUsers(
  params?: { offset?: number; limit?: number },
  options?: UseQueryOptions<UserListResponse, ApiError>
) {
  return useQuery({
    queryKey: [...userKeys.list, params],
    queryFn: () => getSDK().users.listUsers(params),
    ...options,
  })
}

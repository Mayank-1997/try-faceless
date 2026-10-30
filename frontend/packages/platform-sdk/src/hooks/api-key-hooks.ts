import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  ApiKeyResponse,
  ApiKeyWithSecretResponse,
  CreateApiKeyRequest,
  UpdateApiKeyRequest,
  MessageResponse,
  ApiError,
} from '@ai-video-studio/shared-types'

export const apiKeyKeys = {
  all: ['api-keys'] as const,
  list: ['api-keys', 'list'] as const,
}

export function useApiKeys(
  options?: UseQueryOptions<ApiKeyResponse[], ApiError>
) {
  return useQuery({
    queryKey: apiKeyKeys.list,
    queryFn: () => getSDK().apiKeys.listKeys(),
    ...options,
  })
}

export function useCreateApiKey(
  options?: UseMutationOptions<ApiKeyWithSecretResponse, ApiError, CreateApiKeyRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateApiKeyRequest) => getSDK().apiKeys.createKey(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.list })
    },
    ...options,
  })
}

export function useRevokeApiKey(
  options?: UseMutationOptions<MessageResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getSDK().apiKeys.revokeKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.list })
    },
    ...options,
  })
}

export function useUpdateApiKey(
  options?: UseMutationOptions<ApiKeyResponse, ApiError, { id: string; data: UpdateApiKeyRequest }>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => getSDK().apiKeys.updateKey(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.list })
    },
    ...options,
  })
}

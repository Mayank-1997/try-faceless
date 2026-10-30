import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type { SessionListResponse, MessageResponse, ApiError } from '@ai-video-studio/shared-types'

export const sessionKeys = {
  all: ['sessions'] as const,
  list: ['sessions', 'list'] as const,
}

export function useSessions(
  options?: UseQueryOptions<SessionListResponse, ApiError>
) {
  return useQuery({
    queryKey: sessionKeys.list,
    queryFn: () => getSDK().sessions.listSessions(),
    ...options,
  })
}

export function useRevokeSession(
  options?: UseMutationOptions<MessageResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getSDK().sessions.revokeSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.list })
    },
    ...options,
  })
}

export function useRevokeAllSessions(
  options?: UseMutationOptions<MessageResponse, ApiError, void>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => getSDK().sessions.revokeAllSessions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.list })
    },
    ...options,
  })
}

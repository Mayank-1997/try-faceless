import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  ProjectResponse,
  ProjectListResponse,
  CreateProjectRequest,
  UpdateProjectRequest,
  WorkflowResponse,
  MessageResponse,
  ApiError,
} from '@ai-video-studio/shared-types'

export const projectKeys = {
  all: ['projects'] as const,
  list: (params?: Record<string, unknown>) => ['projects', 'list', params] as const,
  detail: (id: string) => ['projects', 'detail', id] as const,
  workflow: (id: string) => ['projects', id, 'workflow'] as const,
}

export function useProjects(
  params?: { status?: string; content_type?: string; offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<ProjectListResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: projectKeys.list(params),
    queryFn: () => getSDK().projects.list(params),
    ...options,
  })
}

export function useProject(
  id: string,
  options?: Omit<UseQueryOptions<ProjectResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => getSDK().projects.getById(id),
    enabled: !!id,
    ...options,
  })
}

export function useCreateProject(
  options?: UseMutationOptions<ProjectResponse, ApiError, CreateProjectRequest>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateProjectRequest) => getSDK().projects.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
    ...options,
  })
}

export function useUpdateProject(
  options?: UseMutationOptions<ProjectResponse, ApiError, { id: string; data: UpdateProjectRequest }>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => getSDK().projects.update(id, data),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(projectKeys.detail(variables.id), data)
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
    ...options,
  })
}

export function useDeleteProject(
  options?: UseMutationOptions<MessageResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getSDK().projects.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
    ...options,
  })
}

export function useProjectWorkflow(
  id: string,
  options?: Omit<UseQueryOptions<WorkflowResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: projectKeys.workflow(id),
    queryFn: async () => {
      try {
        return await getSDK().projects.getWorkflow(id)
      } catch (err) {
        if (err instanceof Error && 'status_code' in err && err.status_code === 404) {
          return null as unknown as WorkflowResponse
        }
        throw err
      }
    },
    enabled: !!id,
    retry: (failureCount, error) => {
      if (error && typeof error === 'object' && 'status_code' in error && error.status_code === 404) {
        return false
      }
      return failureCount < 3
    },
    ...options,
  })
}

export function useStartWorkflow(
  options?: UseMutationOptions<WorkflowResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  const { onSuccess, ...rest } = options ?? {}
  return useMutation({
    mutationFn: (id: string) => getSDK().projects.startWorkflow(id),
    onSuccess: (data, projectId, context) => {
      queryClient.setQueryData(projectKeys.workflow(projectId), data)
      queryClient.invalidateQueries({ queryKey: projectKeys.workflow(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      onSuccess?.(data, projectId, context)
    },
    ...rest,
  })
}

export function useCancelWorkflow(
  options?: UseMutationOptions<MessageResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  const { onSuccess, ...rest } = options ?? {}
  return useMutation({
    mutationFn: (id: string) => getSDK().projects.cancelWorkflow(id),
    onSuccess: (data, projectId, context) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.workflow(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      onSuccess?.(data, projectId, context)
    },
    ...rest,
  })
}

export function useAdvanceWorkflow(
  options?: UseMutationOptions<WorkflowResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  const { onSuccess, ...rest } = options ?? {}
  return useMutation({
    mutationFn: (id: string) => getSDK().projects.advanceWorkflow(id),
    onSuccess: (data, projectId, context) => {
      queryClient.setQueryData(projectKeys.workflow(projectId), data)
      queryClient.invalidateQueries({ queryKey: projectKeys.workflow(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      onSuccess?.(data, projectId, context)
    },
    ...rest,
  })
}

export function useRetryStep(
  options?: UseMutationOptions<WorkflowResponse, ApiError, string>
) {
  const queryClient = useQueryClient()
  const { onSuccess, ...rest } = options ?? {}
  return useMutation({
    mutationFn: (id: string) => getSDK().projects.retryStep(id),
    onSuccess: (data, projectId, context) => {
      queryClient.setQueryData(projectKeys.workflow(projectId), data)
      queryClient.invalidateQueries({ queryKey: projectKeys.workflow(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      onSuccess?.(data, projectId, context)
    },
    ...rest,
  })
}

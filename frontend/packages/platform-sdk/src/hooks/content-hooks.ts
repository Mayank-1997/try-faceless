import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  ResearchResponse,
  ScriptResponse,
  CreateScriptRequest,
  StoryboardResponse,
  SceneResponse,
  SceneListResponse,
  AssetResponse,
  AssetListResponse,
  GenerationJobResponse,
  ApiError,
} from '@ai-video-studio/shared-types'
import { projectKeys } from './project-hooks'

// ---------------------------------------------------------------------------
// Query key factories
// ---------------------------------------------------------------------------
export const contentKeys = {
  research: (projectId: string) => ['projects', projectId, 'research'] as const,
  researchVersions: (projectId: string) => ['projects', projectId, 'research', 'versions'] as const,
  script: (projectId: string) => ['projects', projectId, 'script'] as const,
  scriptVersions: (projectId: string) => ['projects', projectId, 'script', 'versions'] as const,
  storyboard: (projectId: string) => ['projects', projectId, 'storyboard'] as const,
  storyboardVersions: (projectId: string) => ['projects', projectId, 'storyboard', 'versions'] as const,
  scenes: (projectId: string) => ['projects', projectId, 'scenes'] as const,
  scene: (projectId: string, sceneId: string) => ['projects', projectId, 'scenes', sceneId] as const,
  assets: (projectId: string, params?: Record<string, unknown>) => ['projects', projectId, 'assets', params] as const,
  asset: (projectId: string, assetId: string) => ['projects', projectId, 'assets', assetId] as const,
  jobs: (projectId: string, params?: Record<string, unknown>) => ['projects', projectId, 'jobs', params] as const,
}

// ---------------------------------------------------------------------------
// Research hooks
// ---------------------------------------------------------------------------
export function useResearch(
  projectId: string,
  options?: Omit<UseQueryOptions<ResearchResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.research(projectId),
    queryFn: () => getSDK().projects.getResearch(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useResearchVersions(
  projectId: string,
  params?: { offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<ResearchResponse[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.researchVersions(projectId),
    queryFn: () => getSDK().projects.listResearchVersions(projectId, params),
    enabled: !!projectId,
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Script hooks
// ---------------------------------------------------------------------------
export function useScript(
  projectId: string,
  options?: Omit<UseQueryOptions<ScriptResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.script(projectId),
    queryFn: () => getSDK().projects.getScript(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useScriptVersions(
  projectId: string,
  params?: { offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<ScriptResponse[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.scriptVersions(projectId),
    queryFn: () => getSDK().projects.listScriptVersions(projectId, params),
    enabled: !!projectId,
    ...options,
  })
}

export function useCreateScript(
  options?: UseMutationOptions<ScriptResponse, ApiError, { projectId: string; data: CreateScriptRequest }>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, data }) => getSDK().projects.createScript(projectId, data),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(contentKeys.script(variables.projectId), data)
      queryClient.invalidateQueries({ queryKey: contentKeys.scriptVersions(variables.projectId) })
    },
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Storyboard hooks
// ---------------------------------------------------------------------------
export function useStoryboard(
  projectId: string,
  options?: Omit<UseQueryOptions<StoryboardResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.storyboard(projectId),
    queryFn: () => getSDK().projects.getStoryboard(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useStoryboardVersions(
  projectId: string,
  params?: { offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<StoryboardResponse[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.storyboardVersions(projectId),
    queryFn: () => getSDK().projects.listStoryboardVersions(projectId, params),
    enabled: !!projectId,
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Scene hooks
// ---------------------------------------------------------------------------
export function useScenes(
  projectId: string,
  options?: Omit<UseQueryOptions<SceneListResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.scenes(projectId),
    queryFn: () => getSDK().projects.listScenes(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useScene(
  projectId: string,
  sceneId: string,
  options?: Omit<UseQueryOptions<SceneResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.scene(projectId, sceneId),
    queryFn: () => getSDK().projects.getScene(projectId, sceneId),
    enabled: !!projectId && !!sceneId,
    ...options,
  })
}

export function useUpdateScene(
  options?: UseMutationOptions<
    SceneResponse,
    ApiError,
    { projectId: string; sceneId: string; updates: Record<string, unknown> }
  >
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, sceneId, updates }) =>
      getSDK().projects.updateScene(projectId, sceneId, updates),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(contentKeys.scene(variables.projectId, variables.sceneId), data)
      queryClient.invalidateQueries({ queryKey: contentKeys.scenes(variables.projectId) })
    },
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Asset hooks
// ---------------------------------------------------------------------------
export function useAssets(
  projectId: string,
  params?: { asset_type?: string; offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<AssetListResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.assets(projectId, params as Record<string, unknown>),
    queryFn: () => getSDK().projects.listAssets(projectId, params),
    enabled: !!projectId,
    ...options,
  })
}

export function useAsset(
  projectId: string,
  assetId: string,
  options?: Omit<UseQueryOptions<AssetResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.asset(projectId, assetId),
    queryFn: () => getSDK().projects.getAsset(projectId, assetId),
    enabled: !!projectId && !!assetId,
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Generation Job hooks
// ---------------------------------------------------------------------------
export function useGenerationJobs(
  projectId: string,
  params?: { offset?: number; limit?: number },
  options?: Omit<UseQueryOptions<GenerationJobResponse[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: contentKeys.jobs(projectId, params as Record<string, unknown>),
    queryFn: () => getSDK().projects.listJobs(projectId, params),
    enabled: !!projectId,
    ...options,
  })
}

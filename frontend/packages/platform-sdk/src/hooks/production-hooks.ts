import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'
import { getSDK } from '../sdk'
import type {
  CompositionDocumentDTO,
  CreateCompositionRequest,
  UpdateTimelineRequest,
  RenderJobDTO,
  RenderProgressDTO,
  ProjectPackageDTO,
  PreviewResultDTO,
  CreateRenderRequest,
  PublishingPlanDTO,
  PublishingJobDTO,
  PublishingReportDTO,
  CreatePublishingRequest,
  MessageResponse,
  ApiError,
} from '@ai-video-studio/shared-types'

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------
export const productionKeys = {
  composition: (projectId: string) => ['projects', projectId, 'composition'] as const,
  compositionById: (projectId: string, compId: string) =>
    ['projects', projectId, 'composition', compId] as const,
  renders: (projectId: string) => ['projects', projectId, 'renders'] as const,
  render: (projectId: string, jobId: string) =>
    ['projects', projectId, 'renders', jobId] as const,
  renderProgress: (projectId: string, jobId: string) =>
    ['projects', projectId, 'renders', jobId, 'progress'] as const,
  package: (projectId: string) => ['projects', projectId, 'package'] as const,
  publishingPlans: (projectId: string) =>
    ['projects', projectId, 'publishing', 'plans'] as const,
  publishingPlan: (projectId: string, planId: string) =>
    ['projects', projectId, 'publishing', 'plans', planId] as const,
  publishingJobs: (projectId: string) =>
    ['projects', projectId, 'publishing', 'jobs'] as const,
  publishingReports: (projectId: string) =>
    ['projects', projectId, 'publishing', 'reports'] as const,
}

// ---------------------------------------------------------------------------
// Composition hooks
// ---------------------------------------------------------------------------
export function useComposition(
  projectId: string,
  options?: UseQueryOptions<CompositionDocumentDTO, ApiError>
) {
  return useQuery({
    queryKey: productionKeys.composition(projectId),
    queryFn: () => getSDK().production.getComposition(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useBuildComposition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      body,
    }: {
      projectId: string
      body?: Partial<CreateCompositionRequest>
    }) => getSDK().production.buildComposition(projectId, body),
    onSuccess: (data, { projectId }) => {
      qc.setQueryData(productionKeys.composition(projectId), data)
    },
  })
}

export function useUpdateTimeline() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      compositionId,
      body,
    }: {
      projectId: string
      compositionId: string
      body: UpdateTimelineRequest
    }) => getSDK().production.updateTimeline(projectId, compositionId, body),
    onSuccess: (data, { projectId }) => {
      qc.setQueryData(productionKeys.composition(projectId), data)
    },
  })
}

// ---------------------------------------------------------------------------
// Render hooks
// ---------------------------------------------------------------------------
export function useRenders(
  projectId: string,
  options?: UseQueryOptions<RenderJobDTO[], ApiError>
) {
  return useQuery({
    queryKey: productionKeys.renders(projectId),
    queryFn: () => getSDK().production.listRenders(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useRenderProgress(
  projectId: string,
  jobId: string,
  options?: UseQueryOptions<RenderProgressDTO, ApiError>
) {
  return useQuery({
    queryKey: productionKeys.renderProgress(projectId, jobId),
    queryFn: () => getSDK().production.getRenderProgress(projectId, jobId),
    enabled: !!projectId && !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return false
      }
      return 2000
    },
    ...options,
  })
}

export function useSubmitRender() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      body,
    }: {
      projectId: string
      body: CreateRenderRequest
    }) => getSDK().production.submitRender(projectId, body),
    onSuccess: (_, { projectId }) => {
      qc.invalidateQueries({ queryKey: productionKeys.renders(projectId) })
    },
  })
}

export function useCancelRender() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, jobId }: { projectId: string; jobId: string }) =>
      getSDK().production.cancelRender(projectId, jobId),
    onSuccess: (_, { projectId }) => {
      qc.invalidateQueries({ queryKey: productionKeys.renders(projectId) })
    },
  })
}

// ---------------------------------------------------------------------------
// Preview hooks
// ---------------------------------------------------------------------------
export function useGeneratePreview() {
  return useMutation({
    mutationFn: ({
      projectId,
      compositionId,
    }: {
      projectId: string
      compositionId: string
    }) => getSDK().production.generatePreview(projectId, compositionId),
  })
}

// ---------------------------------------------------------------------------
// Project Package hooks
// ---------------------------------------------------------------------------
export function useProjectPackage(
  projectId: string,
  options?: UseQueryOptions<ProjectPackageDTO, ApiError>
) {
  return useQuery({
    queryKey: productionKeys.package(projectId),
    queryFn: () => getSDK().production.getProjectPackage(projectId),
    enabled: !!projectId,
    ...options,
  })
}

// ---------------------------------------------------------------------------
// Publishing hooks
// ---------------------------------------------------------------------------
export function usePublishingPlans(
  projectId: string,
  options?: UseQueryOptions<PublishingPlanDTO[], ApiError>
) {
  return useQuery({
    queryKey: productionKeys.publishingPlans(projectId),
    queryFn: () => getSDK().production.listPublishingPlans(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function usePublishingJobs(
  projectId: string,
  options?: UseQueryOptions<PublishingJobDTO[], ApiError>
) {
  return useQuery({
    queryKey: productionKeys.publishingJobs(projectId),
    queryFn: () => getSDK().production.listPublishingJobs(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function usePublishingReports(
  projectId: string,
  options?: UseQueryOptions<PublishingReportDTO[], ApiError>
) {
  return useQuery({
    queryKey: productionKeys.publishingReports(projectId),
    queryFn: () => getSDK().production.listPublishingReports(projectId),
    enabled: !!projectId,
    ...options,
  })
}

export function useCreatePublishingPlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      body,
    }: {
      projectId: string
      body: CreatePublishingRequest
    }) => getSDK().production.createPublishingPlan(projectId, body),
    onSuccess: (_, { projectId }) => {
      qc.invalidateQueries({ queryKey: productionKeys.publishingPlans(projectId) })
    },
  })
}

export function useExecutePublishing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, planId }: { projectId: string; planId: string }) =>
      getSDK().production.executePublishing(projectId, planId),
    onSuccess: (_, { projectId }) => {
      qc.invalidateQueries({ queryKey: productionKeys.publishingJobs(projectId) })
      qc.invalidateQueries({ queryKey: productionKeys.publishingPlans(projectId) })
    },
  })
}

export function useCancelPublishingJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, jobId }: { projectId: string; jobId: string }) =>
      getSDK().production.cancelPublishingJob(projectId, jobId),
    onSuccess: (_, { projectId }) => {
      qc.invalidateQueries({ queryKey: productionKeys.publishingJobs(projectId) })
    },
  })
}

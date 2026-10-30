import type { ApiClient } from '../api-client'
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
  PublishingTaskDTO,
  MessageResponse,
} from '@ai-video-studio/shared-types'

export class ProductionSDK {
  constructor(private readonly api: ApiClient) {}

  // ------------------------------------------------------------------
  // Composition
  // ------------------------------------------------------------------
  async buildComposition(
    projectId: string,
    body?: Partial<CreateCompositionRequest>
  ): Promise<CompositionDocumentDTO> {
    return this.api.post<CompositionDocumentDTO>(
      `/projects/${projectId}/composition`,
      body ?? {}
    )
  }

  async getComposition(projectId: string): Promise<CompositionDocumentDTO> {
    return this.api.get<CompositionDocumentDTO>(`/projects/${projectId}/composition`)
  }

  async getCompositionById(
    projectId: string,
    compositionId: string
  ): Promise<CompositionDocumentDTO> {
    return this.api.get<CompositionDocumentDTO>(
      `/projects/${projectId}/composition/${compositionId}`
    )
  }

  async updateTimeline(
    projectId: string,
    compositionId: string,
    body: UpdateTimelineRequest
  ): Promise<CompositionDocumentDTO> {
    return this.api.patch<CompositionDocumentDTO>(
      `/projects/${projectId}/composition/${compositionId}/timeline`,
      body
    )
  }

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------
  async submitRender(
    projectId: string,
    body: CreateRenderRequest
  ): Promise<RenderJobDTO> {
    return this.api.post<RenderJobDTO>(`/projects/${projectId}/renders`, body)
  }

  async listRenders(projectId: string): Promise<RenderJobDTO[]> {
    return this.api.get<RenderJobDTO[]>(`/projects/${projectId}/renders`)
  }

  async getRender(projectId: string, jobId: string): Promise<RenderJobDTO> {
    return this.api.get<RenderJobDTO>(`/projects/${projectId}/renders/${jobId}`)
  }

  async getRenderProgress(
    projectId: string,
    jobId: string
  ): Promise<RenderProgressDTO> {
    return this.api.get<RenderProgressDTO>(
      `/projects/${projectId}/renders/${jobId}/progress`
    )
  }

  async cancelRender(
    projectId: string,
    jobId: string
  ): Promise<MessageResponse> {
    return this.api.post<MessageResponse>(
      `/projects/${projectId}/renders/${jobId}/cancel`,
      {}
    )
  }

  // ------------------------------------------------------------------
  // Preview
  // ------------------------------------------------------------------
  async generatePreview(
    projectId: string,
    compositionId: string
  ): Promise<PreviewResultDTO> {
    return this.api.post<PreviewResultDTO>(
      `/projects/${projectId}/composition/${compositionId}/preview`,
      {}
    )
  }

  // ------------------------------------------------------------------
  // Project Package
  // ------------------------------------------------------------------
  async getProjectPackage(projectId: string): Promise<ProjectPackageDTO> {
    return this.api.get<ProjectPackageDTO>(`/projects/${projectId}/package`)
  }

  // ------------------------------------------------------------------
  // Publishing
  // ------------------------------------------------------------------
  async createPublishingPlan(
    projectId: string,
    body: CreatePublishingRequest
  ): Promise<PublishingPlanDTO> {
    return this.api.post<PublishingPlanDTO>(
      `/projects/${projectId}/publishing/plans`,
      body
    )
  }

  async listPublishingPlans(projectId: string): Promise<PublishingPlanDTO[]> {
    return this.api.get<PublishingPlanDTO[]>(
      `/projects/${projectId}/publishing/plans`
    )
  }

  async getPublishingPlan(
    projectId: string,
    planId: string
  ): Promise<PublishingPlanDTO> {
    return this.api.get<PublishingPlanDTO>(
      `/projects/${projectId}/publishing/plans/${planId}`
    )
  }

  async executePublishing(
    projectId: string,
    planId: string
  ): Promise<PublishingJobDTO[]> {
    return this.api.post<PublishingJobDTO[]>(
      `/projects/${projectId}/publishing/plans/${planId}/execute`,
      {}
    )
  }

  async listPublishingJobs(projectId: string): Promise<PublishingJobDTO[]> {
    return this.api.get<PublishingJobDTO[]>(
      `/projects/${projectId}/publishing/jobs`
    )
  }

  async cancelPublishingJob(
    projectId: string,
    jobId: string
  ): Promise<MessageResponse> {
    return this.api.post<MessageResponse>(
      `/projects/${projectId}/publishing/jobs/${jobId}/cancel`,
      {}
    )
  }

  async listPublishingReports(
    projectId: string
  ): Promise<PublishingReportDTO[]> {
    return this.api.get<PublishingReportDTO[]>(
      `/projects/${projectId}/publishing/reports`
    )
  }
}

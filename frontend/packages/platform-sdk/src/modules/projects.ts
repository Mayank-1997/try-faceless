import type { ApiClient } from '../api-client'
import type {
  ProjectResponse,
  ProjectListResponse,
  CreateProjectRequest,
  UpdateProjectRequest,
  WorkflowResponse,
  MessageResponse,
  ResearchResponse,
  ScriptResponse,
  CreateScriptRequest,
  StoryboardResponse,
  SceneResponse,
  SceneListResponse,
  AssetResponse,
  AssetListResponse,
  GenerationJobResponse,
} from '@ai-video-studio/shared-types'

export class ProjectsSDK {
  constructor(private readonly api: ApiClient) {}

  // ------------------------------------------------------------------
  // Project CRUD
  // ------------------------------------------------------------------
  async list(params?: {
    status?: string
    content_type?: string
    offset?: number
    limit?: number
  }): Promise<ProjectListResponse> {
    return this.api.get<ProjectListResponse>('/projects', { params })
  }

  async getById(id: string): Promise<ProjectResponse> {
    return this.api.get<ProjectResponse>(`/projects/${id}`)
  }

  async create(data: CreateProjectRequest): Promise<ProjectResponse> {
    return this.api.post<ProjectResponse>('/projects', data)
  }

  async update(id: string, data: UpdateProjectRequest): Promise<ProjectResponse> {
    return this.api.patch<ProjectResponse>(`/projects/${id}`, data)
  }

  async delete(id: string): Promise<MessageResponse> {
    return this.api.delete<MessageResponse>(`/projects/${id}`)
  }

  // ------------------------------------------------------------------
  // Workflow
  // ------------------------------------------------------------------
  async getWorkflow(id: string): Promise<WorkflowResponse> {
    return this.api.get<WorkflowResponse>(`/projects/${id}/workflow`)
  }

  async startWorkflow(id: string): Promise<WorkflowResponse> {
    return this.api.post<WorkflowResponse>(`/projects/${id}/workflow/start`)
  }

  async cancelWorkflow(id: string): Promise<MessageResponse> {
    return this.api.post<MessageResponse>(`/projects/${id}/workflow/cancel`)
  }

  async advanceWorkflow(id: string): Promise<WorkflowResponse> {
    return this.api.post<WorkflowResponse>(`/projects/${id}/workflow/advance`)
  }

  async retryStep(id: string): Promise<WorkflowResponse> {
    return this.api.post<WorkflowResponse>(`/projects/${id}/workflow/retry`)
  }

  // ------------------------------------------------------------------
  // Research
  // ------------------------------------------------------------------
  async getResearch(projectId: string): Promise<ResearchResponse> {
    return this.api.get<ResearchResponse>(`/projects/${projectId}/research`)
  }

  async listResearchVersions(
    projectId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<ResearchResponse[]> {
    return this.api.get<ResearchResponse[]>(`/projects/${projectId}/research/versions`, { params })
  }

  // ------------------------------------------------------------------
  // Script
  // ------------------------------------------------------------------
  async getScript(projectId: string): Promise<ScriptResponse> {
    return this.api.get<ScriptResponse>(`/projects/${projectId}/script`)
  }

  async listScriptVersions(
    projectId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<ScriptResponse[]> {
    return this.api.get<ScriptResponse[]>(`/projects/${projectId}/script/versions`, { params })
  }

  async createScript(projectId: string, data: CreateScriptRequest): Promise<ScriptResponse> {
    return this.api.post<ScriptResponse>(`/projects/${projectId}/script`, data)
  }

  // ------------------------------------------------------------------
  // Storyboard
  // ------------------------------------------------------------------
  async getStoryboard(projectId: string): Promise<StoryboardResponse> {
    return this.api.get<StoryboardResponse>(`/projects/${projectId}/storyboard`)
  }

  async listStoryboardVersions(
    projectId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<StoryboardResponse[]> {
    return this.api.get<StoryboardResponse[]>(`/projects/${projectId}/storyboard/versions`, { params })
  }

  // ------------------------------------------------------------------
  // Scenes
  // ------------------------------------------------------------------
  async listScenes(projectId: string): Promise<SceneListResponse> {
    return this.api.get<SceneListResponse>(`/projects/${projectId}/scenes`)
  }

  async getScene(projectId: string, sceneId: string): Promise<SceneResponse> {
    return this.api.get<SceneResponse>(`/projects/${projectId}/scenes/${sceneId}`)
  }

  async updateScene(
    projectId: string,
    sceneId: string,
    updates: Record<string, unknown>
  ): Promise<SceneResponse> {
    return this.api.patch<SceneResponse>(`/projects/${projectId}/scenes/${sceneId}`, updates)
  }

  // ------------------------------------------------------------------
  // Assets
  // ------------------------------------------------------------------
  async listAssets(
    projectId: string,
    params?: { asset_type?: string; offset?: number; limit?: number }
  ): Promise<AssetListResponse> {
    return this.api.get<AssetListResponse>(`/projects/${projectId}/assets`, { params })
  }

  async getAsset(projectId: string, assetId: string): Promise<AssetResponse> {
    return this.api.get<AssetResponse>(`/projects/${projectId}/assets/${assetId}`)
  }

  // ------------------------------------------------------------------
  // Generation Jobs
  // ------------------------------------------------------------------
  async listJobs(
    projectId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<GenerationJobResponse[]> {
    return this.api.get<GenerationJobResponse[]>(`/projects/${projectId}/jobs`, { params })
  }

  async downloadOutputs(projectId: string): Promise<Blob> {
    const res = await this.api.axiosInstance.get(`/projects/${projectId}/download`, {
      responseType: 'blob',
    })
    return res.data as Blob
  }

  async downloadVideo(projectId: string): Promise<Blob> {
    const res = await this.api.axiosInstance.get(`/projects/${projectId}/download/video`, {
      responseType: 'blob',
    })
    return res.data as Blob
  }
}

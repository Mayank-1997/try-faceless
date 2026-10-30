import type { ApiClient } from '../api-client'
import type { SessionListResponse, MessageResponse } from '@ai-video-studio/shared-types'

export class SessionsSDK {
  constructor(private client: ApiClient) {}

  async listSessions(): Promise<SessionListResponse> {
    return this.client.get<SessionListResponse>('/sessions')
  }

  async revokeSession(id: string): Promise<MessageResponse> {
    return this.client.delete<MessageResponse>(`/sessions/${id}`)
  }

  async revokeAllSessions(): Promise<MessageResponse> {
    return this.client.delete<MessageResponse>('/sessions')
  }
}

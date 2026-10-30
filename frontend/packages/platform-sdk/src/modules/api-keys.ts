import type { ApiClient } from '../api-client'
import type {
  ApiKeyResponse,
  ApiKeyWithSecretResponse,
  CreateApiKeyRequest,
  UpdateApiKeyRequest,
  MessageResponse,
} from '@ai-video-studio/shared-types'

export class ApiKeysSDK {
  constructor(private client: ApiClient) {}

  async listKeys(): Promise<ApiKeyResponse[]> {
    return this.client.get<ApiKeyResponse[]>('/api-keys')
  }

  async createKey(data: CreateApiKeyRequest): Promise<ApiKeyWithSecretResponse> {
    return this.client.post<ApiKeyWithSecretResponse>('/api-keys', data)
  }

  async revokeKey(id: string): Promise<MessageResponse> {
    return this.client.delete<MessageResponse>(`/api-keys/${id}`)
  }

  async updateKey(id: string, data: UpdateApiKeyRequest): Promise<ApiKeyResponse> {
    return this.client.patch<ApiKeyResponse>(`/api-keys/${id}`, data)
  }
}

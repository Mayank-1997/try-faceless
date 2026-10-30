import type { ApiClient } from '../api-client'
import type {
  UserResponse,
  UserListResponse,
  UserPreferencesResponse,
  UpdateProfileRequest,
  ChangePasswordRequest,
  UpdatePreferencesRequest,
  MessageResponse,
} from '@ai-video-studio/shared-types'

export class UsersSDK {
  constructor(private client: ApiClient) {}

  async getCurrentUser(): Promise<UserResponse> {
    return this.client.get<UserResponse>('/users/me')
  }

  async updateProfile(data: UpdateProfileRequest): Promise<UserResponse> {
    return this.client.put<UserResponse>('/users/me', data)
  }

  async changePassword(data: ChangePasswordRequest): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/users/me/password', data)
  }

  async getPreferences(): Promise<UserPreferencesResponse> {
    return this.client.get<UserPreferencesResponse>('/users/me/preferences')
  }

  async updatePreferences(data: UpdatePreferencesRequest): Promise<UserPreferencesResponse> {
    return this.client.put<UserPreferencesResponse>('/users/me/preferences', data)
  }

  async listUsers(params?: { offset?: number; limit?: number }): Promise<UserListResponse> {
    const query = params
      ? `?offset=${params.offset ?? 0}&limit=${params.limit ?? 20}`
      : ''
    return this.client.get<UserListResponse>(`/users${query}`)
  }
}

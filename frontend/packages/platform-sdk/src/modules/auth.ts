import type { ApiClient } from '../api-client'
import type {
  AuthResponse,
  RegisterRequest,
  LoginRequest,
  RefreshTokenRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  VerifyEmailRequest,
  ResendVerificationRequest,
  MessageResponse,
} from '@ai-video-studio/shared-types'

export class AuthSDK {
  constructor(private client: ApiClient) {}

  async register(data: RegisterRequest): Promise<AuthResponse> {
    return this.client.post<AuthResponse>('/auth/register', data)
  }

  async login(data: LoginRequest): Promise<AuthResponse> {
    return this.client.post<AuthResponse>('/auth/login', data)
  }

  async refresh(data: RefreshTokenRequest): Promise<AuthResponse> {
    return this.client.post<AuthResponse>('/auth/refresh', data)
  }

  async logout(): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/auth/logout')
  }

  async forgotPassword(data: ForgotPasswordRequest): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/auth/forgot-password', data)
  }

  async resetPassword(data: ResetPasswordRequest): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/auth/reset-password', data)
  }

  async verifyEmail(data: VerifyEmailRequest): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/auth/verify-email', data)
  }

  async resendVerification(data: ResendVerificationRequest): Promise<MessageResponse> {
    return this.client.post<MessageResponse>('/auth/resend-verification', data)
  }
}

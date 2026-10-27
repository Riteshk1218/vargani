import type { Language, TokenResponse, User, VerificationResponse } from '../types/api'
import { api } from './apiClient'

export interface RegisterInput {
  full_name: string
  email?: string
  mobile?: string
  password: string
  preferred_language: Language
}

export const authService = {
  register: (input: RegisterInput) => api.post<VerificationResponse>('/auth/register/', input).then((r) => r.data),
  verify: (destination: string, code: string) =>
    api.post<TokenResponse>('/auth/verify/', { destination, code }).then((r) => r.data),
  resendVerification: (destination: string) =>
    api.post<VerificationResponse>('/auth/verify/resend/', { destination }).then((r) => r.data),
  login: (identifier: string, password: string) =>
    api.post<TokenResponse>('/auth/login/', { identifier, password }).then((r) => r.data),
  logout: () => api.post('/auth/logout/', {}),
  forgotPassword: (identifier: string) =>
    api.post<{ detail: string; debug_code?: string }>('/auth/password/forgot/', { identifier }).then((r) => r.data),
  resetPassword: (identifier: string, code: string, new_password: string) =>
    api.post<{ detail: string }>('/auth/password/reset/', { identifier, code, new_password }).then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post<TokenResponse>('/auth/password/change/', { current_password, new_password }).then((r) => r.data),
  me: () => api.get<User>('/me/').then((r) => r.data),
  updateMe: (data: Partial<Pick<User, 'full_name' | 'preferred_language' | 'theme_color'>>) =>
    api.patch<User>('/me/', data).then((r) => r.data),
}

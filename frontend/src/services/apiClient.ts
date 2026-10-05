import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import i18n from '../i18n'
import type { ApiErrorBody } from '../types/api'
import { session } from './session'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number
  code: string
  details: Record<string, string[]>
  requestId: string | null

  constructor(status: number, code: string, message: string, details: Record<string, string[]> = {}, requestId: string | null = null) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }

  fieldError(field: string): string | undefined {
    return this.details[field]?.[0]
  }
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { 'X-Client-Type': 'web' },
})

api.interceptors.request.use((config) => {
  const token = session.getAccessToken()
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  const orgId = session.getOrganizationId()
  if (orgId && !config.headers.has('X-Organization-ID')) config.headers.set('X-Organization-ID', orgId)
  config.headers.set('Accept-Language', i18n.language || 'en')
  return config
})

let refreshing: Promise<string | null> | null = null

/** Single-flight refresh using the HttpOnly cookie. Returns the new access token or null. */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = axios
      .post<{ access: string }>(`${API_BASE_URL}/auth/refresh/`, {}, { withCredentials: true, headers: { 'X-Client-Type': 'web' } })
      .then((response) => {
        session.setAccessToken(response.data.access)
        return response.data.access
      })
      .catch(() => {
        session.setAccessToken(null)
        return null
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

let onSessionExpired: () => void = () => {}
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const config = error.config as RetriableConfig | undefined
    const isAuthCall = config?.url?.includes('/auth/')
    if (error.response?.status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true
      const token = await refreshAccessToken()
      if (token) return api(config as AxiosRequestConfig)
      onSessionExpired()
    }
    throw toApiError(error)
  },
)

type DetailNode = { code: string; message: string } | DetailNode[] | { [key: string]: DetailNode }

function isMessage(node: unknown): node is { code: string; message: string } {
  return typeof node === 'object' && node !== null && 'message' in node && 'code' in node
}

/** Nested errors (e.g. one line of a payment) become dotted keys: {"lines": {"0": {"amount": [...]}}} → "lines.0.amount". */
function flattenDetails(prefix: string, node: unknown, out: Record<string, string[]>) {
  const key = (part: string | number) => (prefix ? `${prefix}.${part}` : String(part))
  if (Array.isArray(node)) {
    node.forEach((item, index) => {
      if (isMessage(item)) (out[prefix] ??= []).push(item.message)
      else flattenDetails(key(index), item, out)
    })
  } else if (isMessage(node)) {
    ;(out[prefix] ??= []).push(node.message)
  } else if (typeof node === 'object' && node !== null) {
    for (const [field, child] of Object.entries(node as Record<string, DetailNode>)) flattenDetails(key(field), child, out)
  }
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined
    if (body?.error) {
      const details: Record<string, string[]> = {}
      flattenDetails('', body.error.details ?? {}, details)
      return new ApiError(error.response!.status, body.error.code, body.error.message, details, body.request_id)
    }
    if (!error.response) return new ApiError(0, 'network_error', i18n.t('errors.network'))
    return new ApiError(error.response.status, 'error', i18n.t('errors.generic'))
  }
  return new ApiError(0, 'error', i18n.t('errors.generic'))
}

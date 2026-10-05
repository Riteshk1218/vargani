import type {
  AppNotification,
  CheckoutOptions,
  GatewaySettings,
  Paginated,
  Payment,
  PortalMe,
  PortalSummary,
  Receipt,
  ReminderResult,
  TokenResponse,
  VerificationResponse,
} from '../types/api'
import { api } from './apiClient'

/** Members log in with their mobile number and a one-time code; no password. */
export const memberAuthService = {
  requestCode: (mobile: string) => api.post<VerificationResponse>('/auth/otp/request/', { mobile }).then((r) => r.data),
  verifyCode: (mobile: string, code: string) => api.post<TokenResponse>('/auth/otp/verify/', { mobile, code }).then((r) => r.data),
}

type EventParam = { event?: string }

export const portalService = {
  me: () => api.get<PortalMe>('/portal/me/').then((r) => r.data),
  summary: (params: EventParam) => api.get<PortalSummary>('/portal/summary/', { params }).then((r) => r.data),
  payments: (params: EventParam) => api.get<Payment[]>('/portal/payments/', { params }).then((r) => r.data),
  receipts: (params: EventParam) => api.get<Receipt[]>('/portal/receipts/', { params }).then((r) => r.data),
  receiptPdf: (id: string) => api.get<Blob>(`/portal/receipts/${id}/pdf/`, { responseType: 'blob' }).then((r) => r.data),
  startPayment: (event: string, lines: { contribution_type: string; amount: string }[]) =>
    api.post<{ payment: string; checkout: CheckoutOptions }>('/portal/pay/', { event, lines }).then((r) => r.data),
  verifyPayment: (body: { order_id: string; payment_id: string; signature: string }) =>
    api.post<Payment>('/portal/pay/verify/', body).then((r) => r.data),
}

export const notificationService = {
  list: (params: { page?: number; unread?: boolean } = {}) =>
    api.get<Paginated<AppNotification>>('/notifications/', { params }).then((r) => r.data),
  unreadCount: () => api.get<{ unread: number }>('/notifications/unread-count/').then((r) => r.data.unread),
  read: (id: string) => api.post<AppNotification>(`/notifications/${id}/read/`).then((r) => r.data),
  readAll: () => api.post<{ marked: number }>('/notifications/read-all/').then((r) => r.data),
  announce: (title: string, message: string) => api.post<{ sent: number }>('/announcements/', { title, message }).then((r) => r.data),
}

export const reminderService = {
  send: (contributionTypeId: string) => api.post<ReminderResult>(`/contribution-types/${contributionTypeId}/remind/`).then((r) => r.data),
}

export interface GatewayInput {
  key_id?: string
  key_secret?: string
  webhook_secret?: string
  is_active?: boolean
}

export const gatewayService = {
  get: () => api.get<GatewaySettings>('/gateway/config/').then((r) => r.data),
  save: (input: GatewayInput) => api.put<GatewaySettings>('/gateway/config/', input).then((r) => r.data),
}

interface RazorpayResponse {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface RazorpayInstance {
  open: () => void
  on: (event: string, handler: (response: unknown) => void) => void
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance
  }
}

let checkoutScript: Promise<void> | null = null

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  checkoutScript ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      checkoutScript = null
      reject(new Error('checkout_unavailable'))
    }
    document.body.appendChild(script)
  })
  return checkoutScript
}

/**
 * Opens Razorpay Checkout. Resolves with the signed result when the member pays, or null when they close it.
 * The payment only counts once the API has checked the signature (or the webhook arrives).
 */
export async function openCheckout(options: CheckoutOptions, language: string): Promise<RazorpayResponse | null> {
  await loadCheckout()
  return new Promise((resolve, reject) => {
    const instance = new window.Razorpay!({
      key: options.key,
      order_id: options.order_id,
      amount: options.amount,
      currency: options.currency,
      name: options.name,
      description: options.description,
      prefill: options.prefill,
      config: { display: { language } },
      handler: (response: RazorpayResponse) => resolve(response),
      modal: { ondismiss: () => resolve(null) },
    })
    instance.on('payment.failed', () => reject(new Error('payment_failed')))
    instance.open()
  })
}

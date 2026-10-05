import type {
  Contribution,
  ContributionType,
  Fund,
  MoneyBreakdown,
  OutstandingReport,
  Paginated,
  Payment,
  PaymentInput,
  Receipt,
} from '../types/api'
import { api } from './apiClient'

type ListParams = Record<string, string | number | boolean | undefined>

export type FundInput = Partial<Pick<Fund, 'event' | 'name' | 'description' | 'target_amount' | 'is_active'>>
export type ContributionTypeInput = Partial<Omit<ContributionType, 'id' | 'fund_name' | 'created_at' | 'updated_at'>>

export const fundService = {
  list: (event: string) => api.get<Paginated<Fund>>('/funds/', { params: { event, page_size: 100 } }).then((r) => r.data),
  create: (input: FundInput) => api.post<Fund>('/funds/', input).then((r) => r.data),
  update: (id: string, input: FundInput) => api.patch<Fund>(`/funds/${id}/`, input).then((r) => r.data),
}

export const contributionTypeService = {
  list: (event: string, params: ListParams = {}) =>
    api.get<Paginated<ContributionType>>('/contribution-types/', { params: { event, page_size: 100, ...params } }).then((r) => r.data),
  create: (input: ContributionTypeInput) => api.post<ContributionType>('/contribution-types/', input).then((r) => r.data),
  update: (id: string, input: ContributionTypeInput) => api.patch<ContributionType>(`/contribution-types/${id}/`, input).then((r) => r.data),
  outstanding: (id: string) => api.get<OutstandingReport>(`/contribution-types/${id}/outstanding/`).then((r) => r.data),
}

export const paymentService = {
  list: (params: ListParams) => api.get<Paginated<Payment>>('/payments/', { params }).then((r) => r.data),
  get: (id: string) => api.get<Payment>(`/payments/${id}/`).then((r) => r.data),
  /** The idempotency key makes a retry after a network error return the first payment instead of a duplicate. */
  record: (input: PaymentInput, idempotencyKey: string) =>
    api.post<Payment>('/collections/', input, { headers: { 'Idempotency-Key': idempotencyKey } }).then((r) => r.data),
  updateNotes: (id: string, notes: string) => api.patch<Payment>(`/payments/${id}/`, { notes }).then((r) => r.data),
  changeStatus: (id: string, action: 'confirm' | 'cancel' | 'fail', reason = '') =>
    api.post<Payment>(`/payments/${id}/${action}/`, { reason }).then((r) => r.data),
}

export const contributionService = {
  list: (params: ListParams) => api.get<Paginated<Contribution>>('/contributions/', { params }).then((r) => r.data),
  summary: (event: string) => api.get<MoneyBreakdown>('/contributions/summary/', { params: { event } }).then((r) => r.data),
}

export const receiptService = {
  list: (params: ListParams) => api.get<Paginated<Receipt>>('/receipts/', { params }).then((r) => r.data),
  get: (id: string) => api.get<Receipt>(`/receipts/${id}/`).then((r) => r.data),
}

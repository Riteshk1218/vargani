import type {
  AuditEntry,
  Expense,
  ExpenseAttachment,
  ExpenseCategory,
  ExpenseInput,
  ExportFormat,
  ExportJob,
  OtherIncome,
  OtherIncomeInput,
  Paginated,
  ReportData,
  ReportInfo,
} from '../types/api'
import { api } from './apiClient'

type ListParams = Record<string, string | number | boolean | undefined>

export const expenseCategoryService = {
  list: () => api.get<ExpenseCategory[]>('/expense-categories/').then((r) => r.data),
  create: (name: string) => api.post<ExpenseCategory>('/expense-categories/', { name }).then((r) => r.data),
  update: (id: string, input: Partial<Pick<ExpenseCategory, 'name' | 'is_active'>>) =>
    api.patch<ExpenseCategory>(`/expense-categories/${id}/`, input).then((r) => r.data),
}

export type ExpenseAction = 'submit' | 'approve' | 'reject' | 'void'

export const expenseService = {
  list: (params: ListParams) => api.get<Paginated<Expense>>('/expenses/', { params }).then((r) => r.data),
  get: (id: string) => api.get<Expense>(`/expenses/${id}/`).then((r) => r.data),
  create: (input: ExpenseInput) => api.post<Expense>('/expenses/', input).then((r) => r.data),
  update: (id: string, input: Partial<ExpenseInput>) => api.patch<Expense>(`/expenses/${id}/`, input).then((r) => r.data),
  act: (id: string, action: ExpenseAction, reason = '') => api.post<Expense>(`/expenses/${id}/${action}/`, { reason }).then((r) => r.data),
  upload: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ExpenseAttachment>(`/expenses/${id}/attachments/`, form).then((r) => r.data)
  },
  download: (id: string, attachmentId: string) =>
    api.get<Blob>(`/expenses/${id}/attachments/${attachmentId}/`, { responseType: 'blob' }).then((r) => r.data),
  removeAttachment: (id: string, attachmentId: string) => api.delete(`/expenses/${id}/attachments/${attachmentId}/`),
}

export const otherIncomeService = {
  list: (params: ListParams) => api.get<Paginated<OtherIncome>>('/other-income/', { params }).then((r) => r.data),
  create: (input: OtherIncomeInput) => api.post<OtherIncome>('/other-income/', input).then((r) => r.data),
  update: (id: string, input: Pick<OtherIncome, 'description' | 'reference_number'>) =>
    api.patch<OtherIncome>(`/other-income/${id}/`, input).then((r) => r.data),
  void: (id: string, reason: string) => api.post<OtherIncome>(`/other-income/${id}/void/`, { reason }).then((r) => r.data),
}

export const reportService = {
  list: () => api.get<ReportInfo[]>('/reports/').then((r) => r.data),
  get: (type: string, filters: ListParams) => api.get<ReportData>(`/reports/${type}/`, { params: filters }).then((r) => r.data),
  startExport: (type: string, format: ExportFormat, filters: ListParams) =>
    api.post<ExportJob>(`/reports/${type}/exports/`, { format, filters }).then((r) => r.data),
  job: (id: string) => api.get<ExportJob>(`/exports/${id}/`).then((r) => r.data),
  download: (id: string) => api.get<Blob>(`/exports/${id}/download/`, { responseType: 'blob' }).then((r) => r.data),
}

/** Starts an export and waits for the file (exports run in the background on the server). */
export async function exportReport(type: string, format: ExportFormat, filters: ListParams): Promise<{ blob: Blob; name: string }> {
  let job = await reportService.startExport(type, format, filters)
  for (let attempt = 0; job.status === 'pending' || job.status === 'running'; attempt++) {
    if (attempt > 120) throw new Error('timeout')
    await new Promise((resolve) => setTimeout(resolve, Math.min(500 + attempt * 250, 3000)))
    job = await reportService.job(job.id)
  }
  if (job.status === 'failed') throw new Error(job.error || 'failed')
  return { blob: await reportService.download(job.id), name: job.file_name }
}

export const auditService = {
  list: (params: ListParams) => api.get<Paginated<AuditEntry>>('/audit-logs/', { params }).then((r) => r.data),
}

import type { DashboardSummary } from '../types/api'
import { api } from './apiClient'

export const dashboardService = {
  summary: (event?: string | null) =>
    api.get<DashboardSummary>('/dashboard/summary/', { params: event ? { event } : {} }).then((r) => r.data),
}

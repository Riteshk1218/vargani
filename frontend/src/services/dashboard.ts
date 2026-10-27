import type { DashboardSummary } from '../types/api'
import { api } from './apiClient'

export const dashboardService = {
  /** `dateFrom` / `dateTo` (YYYY-MM-DD) narrow the money and pavti numbers to those days. */
  summary: (event?: string | null, dateFrom?: string, dateTo?: string) =>
    api
      .get<DashboardSummary>('/dashboard/summary/', {
        params: { ...(event ? { event } : {}), ...(dateFrom ? { date_from: dateFrom } : {}), ...(dateTo ? { date_to: dateTo } : {}) },
      })
      .then((r) => r.data),
}

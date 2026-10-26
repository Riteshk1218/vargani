import type { ExpenseStatus, FollowUpState, IncomeSource, PavtiStatus, PaymentMode, PaymentStatus } from '../types/api'

/** Modes a person can record by hand. "online" is reserved for payment-gateway payments. */
export const MANUAL_MODES: PaymentMode[] = ['cash', 'upi', 'bank_transfer', 'cheque', 'other']

export const PAYMENT_TONE: Record<PaymentStatus, 'green' | 'amber' | 'red' | 'gray'> = {
  successful: 'green',
  pending: 'amber',
  failed: 'red',
  cancelled: 'gray',
  refunded: 'gray',
  deleted: 'red',
}

export const EXPENSE_STATUSES: ExpenseStatus[] = ['draft', 'submitted', 'approved', 'rejected', 'void']

export const EXPENSE_TONE: Record<ExpenseStatus, 'green' | 'amber' | 'red' | 'gray' | 'brand'> = {
  draft: 'gray',
  submitted: 'amber',
  approved: 'green',
  rejected: 'red',
  void: 'gray',
}

export const INCOME_SOURCES: IncomeSource[] = ['donation_box', 'sponsorship', 'interest', 'sale', 'other']

export const PAVTI_TONE: Record<PavtiStatus, 'green' | 'amber' | 'red'> = {
  paid: 'green',
  partly_paid: 'amber',
  unpaid: 'red',
}

export const FOLLOW_UP_TONE: Record<FollowUpState, 'red' | 'amber' | 'gray'> = {
  overdue: 'red',
  today: 'amber',
  upcoming: 'gray',
}

/** Today in the browser's time zone, as YYYY-MM-DD (for date inputs). */
export function todayIso(offsetDays = 0) {
  const now = new Date()
  now.setDate(now.getDate() + offsetDays)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

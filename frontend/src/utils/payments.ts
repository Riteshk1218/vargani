import type { ExpenseStatus, IncomeSource, PaymentMode, PaymentStatus } from '../types/api'

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

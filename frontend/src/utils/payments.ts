import type { PaymentMode, PaymentStatus } from '../types/api'

/** Modes a person can record by hand. "online" is reserved for payment-gateway payments. */
export const MANUAL_MODES: PaymentMode[] = ['cash', 'upi', 'bank_transfer', 'cheque', 'other']

export const PAYMENT_TONE: Record<PaymentStatus, 'green' | 'amber' | 'red' | 'gray'> = {
  successful: 'green',
  pending: 'amber',
  failed: 'red',
  cancelled: 'gray',
  refunded: 'gray',
}

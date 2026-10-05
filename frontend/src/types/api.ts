export type Language = 'en' | 'mr' | 'hi'

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, { code: string; message: string }[]> }
  request_id: string | null
}

export interface User {
  id: string
  full_name: string
  email: string | null
  mobile: string | null
  preferred_language: Language
  email_verified_at: string | null
  mobile_verified_at: string | null
  is_platform_admin: boolean
  date_joined: string
}

export interface TokenResponse {
  access: string
  refresh?: string
  user: User
}

export interface VerificationResponse {
  verification: { destination: string; channel?: 'email' | 'sms' }
  debug_code?: string
}

export interface RoleSummary {
  id: string
  code: string
  name: string
}

export interface Role extends RoleSummary {
  description: string
  is_system: boolean
  permissions: Record<string, string>
}

export interface Organization {
  id: string
  slug: string
  name: string
  address_line1: string
  address_line2: string
  city: string
  district: string
  state: string
  pincode: string
  country: string
  phone: string
  email: string
  website: string
  description: string
  registration_type: string
  registration_number: string
  default_language: Language
  receipt_language: Language
  timezone: string
  currency: string
  logo_url: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface MyOrganization {
  id: string
  name: string
  logo_url: string | null
  role: RoleSummary
  membership_id: string
}

export interface FinancialYear {
  id: string
  label: string
  start_date: string
  end_date: string
  status: 'open' | 'closed'
  is_current: boolean
  created_at: string
  updated_at: string
}

export interface MyOrganizationDetail {
  organization: Organization
  membership_id: string
  role: RoleSummary
  permissions: Record<string, string>
  current_financial_year: FinancialYear | null
}

export interface OrganizationSettings {
  allow_unassigned_collection: boolean
  require_expense_approval: boolean
  member_portal_enabled: boolean
}

export type EventTemplateCode = 'festival' | 'fundraising' | 'membership' | 'society' | 'custom'
export type EventStatus = 'draft' | 'active' | 'closed' | 'archived'
export type EventModules = Partial<Record<'contributions' | 'monthly' | 'expenses' | 'collectors' | 'member_portal', boolean>>

export interface EventItem {
  id: string
  name: string
  template: EventTemplateCode
  code: string
  financial_year: string
  financial_year_label: string
  start_date: string | null
  end_date: string | null
  status: EventStatus
  modules: EventModules
  target_amount: string | null
  description: string
  thank_you_message: string
  created_at: string
  updated_at: string
}

export interface EventTemplate {
  code: EventTemplateCode
  name: string
  description: string
  modules: EventModules
}

export interface EventParticipant {
  id: string
  event: string
  person: string
  person_name: string
  person_mobile: string
  participation_role: 'participant' | 'volunteer' | 'karyakarta' | 'guest'
  status: 'active' | 'inactive'
  notes: string
  created_at: string
}

export type PersonType = 'member' | 'karyakarta' | 'volunteer' | 'donor' | 'supporter' | 'other'

export interface Person {
  id: string
  full_name: string
  mobile: string
  alt_mobile: string
  email: string
  unit: string
  building: string
  area: string
  address_line: string
  city: string
  pincode: string
  person_types: PersonType[]
  notes: string
  is_active: boolean
  has_login: boolean
  created_at: string
  updated_at: string
}

export interface Member {
  id: string
  user: { id: string; full_name: string; email: string | null; mobile: string | null }
  role: RoleSummary
  status: 'active' | 'suspended' | 'removed'
  joined_at: string
}

export interface Invitation {
  id: string
  full_name: string
  email: string | null
  mobile: string | null
  role: RoleSummary
  status: 'pending' | 'accepted' | 'revoked' | 'expired'
  expires_at: string
  created_at: string
  invite_url?: string
}

export interface InvitationPreview {
  valid: boolean
  organization?: { name: string; logo_url: string | null }
  role?: { code: string; name: string }
  expires_at?: string
}

export interface MoneyBreakdown {
  collected: string
  contributors: number
  payments: number
  by_type: { id: string; name: string; total: string; count: number }[]
  by_fund: { id: string | null; name: string | null; total: string }[]
  by_month: { month: string; total: string }[]
  by_mode: { mode: PaymentMode; total: string; count: number }[]
  target_amount: string | null
}

export interface FinancialSummary extends MoneyBreakdown {
  pending_payments: number
  income: string
  expenses: string | null
  balance: string
  recent_payments: { id: string; payer_name: string; amount: string; mode: PaymentMode; paid_at: string; receipt_number: string | null }[]
}

export interface DashboardSummary {
  events: { total: number; active: number }
  people?: { total: number; active: number }
  members?: { total: number }
  current_financial_year: { id: string; label: string } | null
  financial: FinancialSummary | null
  event?: { id: string; name: string; status: EventStatus; target_amount: string | null; participants: number | null }
}

export interface Fund {
  id: string
  event: string
  name: string
  description: string
  target_amount: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ContributionKind = 'one_time' | 'recurring_monthly'

export interface ContributionType {
  id: string
  event: string
  fund: string | null
  fund_name: string | null
  name: string
  kind: ContributionKind
  suggested_min: string | null
  suggested_max: string | null
  target_amount: string | null
  is_mandatory: boolean
  start_date: string | null
  end_date: string | null
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type PaymentMode = 'cash' | 'upi' | 'bank_transfer' | 'cheque' | 'online' | 'other'
export type PaymentStatus = 'pending' | 'successful' | 'failed' | 'cancelled' | 'refunded'
export type ContributionStatus = 'pending' | 'confirmed' | 'cancelled' | 'refunded'

export interface PaymentLine {
  id: string
  contribution_type: string
  contribution_type_name: string
  fund: string | null
  fund_name: string | null
  period_month: string | null
  amount: string
  status: ContributionStatus
  notes: string
}

export interface ReceiptRef {
  id: string
  receipt_number: string
  status: 'issued' | 'void'
  issued_at: string
}

export interface Payment {
  id: string
  event: string
  event_name: string
  payer: string
  payer_name: string
  payer_mobile: string
  amount: string
  mode: PaymentMode
  status: PaymentStatus
  paid_at: string
  reference_number: string
  cheque_bank: string
  cheque_date: string | null
  collector_name: string | null
  notes: string
  status_reason: string
  lines: PaymentLine[]
  receipt: ReceiptRef | null
  created_at: string
}

export interface PaymentInput {
  event: string
  payer: string
  mode: PaymentMode
  status?: 'successful' | 'pending'
  paid_at?: string
  amount?: string
  reference_number?: string
  cheque_bank?: string
  cheque_date?: string | null
  notes?: string
  lines: { contribution_type: string; amount: string; period_month?: string | null; notes?: string }[]
}

export interface Contribution {
  id: string
  event: string
  person: string
  person_name: string
  contribution_type: string
  contribution_type_name: string
  fund: string | null
  fund_name: string | null
  payment: string
  mode: PaymentMode
  period_month: string | null
  amount: string
  contributed_on: string
  status: ContributionStatus
  collector_name: string | null
  notes: string
  created_at: string
}

export interface ReceiptSnapshot {
  organization: {
    name: string
    address: string
    phone: string
    email: string
    registration_type: string
    registration_number: string
    logo: string | null
  }
  person: { name: string; mobile: string; address: string }
  event: { name: string; code: string }
  financial_year: string
  lines: { contribution_type: string; fund: string | null; period_month: string | null; amount: string }[]
  total: string
  currency: string
  mode: PaymentMode
  reference_number: string
  cheque_bank: string
  cheque_date: string | null
  paid_at: string
  collector: string | null
  thank_you_message: string
}

export interface Receipt {
  id: string
  receipt_number: string
  status: 'issued' | 'void'
  issued_at: string
  language: string
  event: string
  payment: string
  payer: string
  payer_name: string
  amount: string
  mode: PaymentMode
  void_reason: string
  voided_at: string | null
  replaces_receipt: string | null
  snapshot: ReceiptSnapshot
  logo_url: string | null
}

export interface OutstandingReport {
  expected_per_person: string
  participants: number
  total_expected: string
  total_paid: string
  total_due: string
  people_with_dues: number
  results: { person: string; person_name: string; mobile: string; expected: string; paid: string; due: string }[]
}

export type Language = 'en' | 'mr' | 'hi'

/** The app's main color. */
export type ThemeColor = 'orange' | 'red' | 'maroon' | 'pink' | 'purple' | 'indigo' | 'blue' | 'teal' | 'green'

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
  /** Set by an organization admin for logins without an email or mobile number. */
  username: string | null
  email: string | null
  mobile: string | null
  preferred_language: Language
  /** The user's own app color; empty uses the organization's color. */
  theme_color: ThemeColor | ''
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
  member_portal_enabled: boolean
  /** The organization's app color, the default for everyone in it. */
  theme_color: ThemeColor
  form_studio: FormStudio
}

/** Collect form fields whose name an Organization Admin can change in the admin studio. */
export type StudioLabelField =
  | 'payer'
  | 'contribution_type'
  | 'month'
  | 'amount'
  | 'received'
  | 'follow_up_on'
  | 'mode'
  | 'paid_on'
  | 'reference'
  | 'cheque_number'
  | 'cheque_bank'
  | 'cheque_date'
  | 'notes'

/** A dropdown the organization added to Collect. `key` is empty until the server saves it. */
export interface StudioField {
  key?: string
  label: string
  options: string[]
  required: boolean
  active: boolean
}

/** Admin studio: how the Collect form looks in this organization. */
export interface FormStudio {
  labels: Partial<Record<StudioLabelField, string>>
  modes: Partial<Record<PaymentMode, { label: string; hidden: boolean }>>
  custom_fields: StudioField[]
}

export interface OrganizationSettings {
  allow_unassigned_collection: boolean
  require_expense_approval: boolean
  member_portal_enabled: boolean
  auto_reminders: boolean
  theme_color: ThemeColor
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
  created_by_name?: string | null
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
  linked_user: string | null
  linked_user_name: string | null
  created_at: string
  created_by_name?: string | null
  updated_at: string
}

export interface Member {
  id: string
  user: { id: string; full_name: string; username: string | null; email: string | null; mobile: string | null }
  role: RoleSummary
  status: 'active' | 'suspended' | 'removed'
  can_download: boolean | null
  can_reset_password: boolean
  joined_at: string
  /** Only on the reply to adding a user: false when the person already had a login (and kept their password). */
  new_login?: boolean
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
  email_sent?: boolean
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
  other_income: string
  income: string
  expenses: string
  balance: string
  expenses_by_category: { id: string; name: string; total: string }[]
  expenses_by_month: { month: string; total: string }[]
  pending_expenses: number
  recent_payments: { id: string; payer_name: string; amount: string; mode: PaymentMode; paid_at: string; receipt_number: string | null }[]
}

export interface DashboardSummary {
  events: { total: number; active: number }
  people?: { total: number; active: number }
  members?: { total: number }
  current_financial_year: { id: string; label: string } | null
  financial: FinancialSummary | null
  event?: { id: string; name: string; status: EventStatus; target_amount: string | null; participants: number | null }
  /** Pavtis still owing money (door-to-door follow-up), for roles that see payments. */
  follow_ups?: { overdue: number; due_today: number; owing: number; balance: string; paid?: number }
  /** The days the money and pavti numbers cover, when a date range was asked for. */
  dates?: { from: string | null; to: string | null }
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
export type PaymentStatus = 'pending' | 'successful' | 'failed' | 'cancelled' | 'refunded' | 'deleted'
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
  /** This line pays a balance kept on a pavti. */
  towards_balance?: boolean
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
  payer: string | null
  payer_name: string
  payer_mobile: string
  is_anonymous: boolean
  financial_year: string
  financial_year_label: string
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
  /** Still owed on this pavti. */
  balance_due: string
  pavti_status: PavtiStatus | null
  /** Kept or pays a balance: only the line amounts can be corrected. */
  keeps_balance?: boolean
  /** When to go back for the money still owed. */
  follow_up_on: string | null
  follow_up_state: FollowUpState | null
  /** The organization's own dropdowns answered on this collection. */
  custom_fields: { key: string; label: string; value: string }[]
  created_at: string
  created_by_name?: string | null
}

export type PavtiStatus = 'unpaid' | 'partly_paid' | 'paid'
export type FollowUpState = 'overdue' | 'today' | 'upcoming'

/** A later visit to the same pavti: money received now (may be 0) and the next follow-up date. */
export interface PavtiVisitInput {
  received?: string
  mode?: PaymentMode
  reference_number?: string
  follow_up_on?: string | null
}

/** A contributor added while collecting. */
export interface NewPersonInput {
  full_name: string
  mobile?: string
  area?: string
  address_line?: string
}

export interface PaymentInput {
  event: string
  /** Empty for an anonymous (no name) collection. */
  payer: string | null
  new_person?: NewPersonInput | null
  mode: PaymentMode
  status?: 'successful' | 'pending'
  paid_at?: string
  amount?: string
  reference_number?: string
  cheque_bank?: string
  cheque_date?: string | null
  notes?: string
  lines: { contribution_type?: string; amount: string; period_month?: string | null; notes?: string; due?: string }[]
  /** Money that came now, when less than the total: the rest is kept as a balance for the person. */
  received?: string
  /** When to go back for the balance. */
  follow_up_on?: string | null
  replaces_receipt?: string
  /** Answers to the organization's own dropdowns: field key -> option picked. */
  custom_fields?: Record<string, string>
}

/** A balance (baaki): money a person still owes on a receipt given before all of it came. */
export interface Due {
  id: string
  event: string
  person: string
  person_name: string
  person_mobile: string
  contribution_type: string
  contribution_type_name: string
  period_month: string | null
  amount: string
  paid: string
  remaining: string
  status: 'open' | 'cancelled'
  status_reason: string
  payment: string
  receipt_number: string | null
  collector_name: string | null
  created_at: string
  created_by_name?: string | null
}

/** Organization Admin edit: send only what changes; `lines` replaces every line. */
export type PaymentEditInput = Partial<
  Pick<PaymentInput, 'payer' | 'new_person' | 'mode' | 'paid_at' | 'reference_number' | 'cheque_bank' | 'cheque_date' | 'notes' | 'lines'>
> & {
  /** Line id -> corrected amount (on a pavti with a balance, the balance moves to match). */
  line_amounts?: Record<string, string>
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
  created_by_name?: string | null
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
  person: { name: string; mobile: string; address: string; anonymous?: boolean }
  event: { name: string; code: string }
  financial_year: string
  lines: { contribution_type: string; fund: string | null; period_month: string | null; amount: string; towards_balance?: boolean }[]
  total: string
  /** What the person still owes after this receipt (receipts issued before balances existed have none). */
  balance_lines?: { contribution_type: string; period_month: string | null; amount: string }[]
  balance_total?: string
  currency: string
  mode: PaymentMode
  /** The organization's own name for the mode, when it set one. */
  mode_label?: string
  /** The organization's own dropdowns, with the names they had when the receipt was issued. */
  custom_fields?: { label: string; value: string }[]
  reference_number: string
  cheque_bank: string
  cheque_date: string | null
  paid_at: string
  timezone?: string
  collector: string | null
  /** Printed above "Authorised signatory": who collected the money (older receipts: the collector). */
  signatory?: string | null
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
  payer: string | null
  payer_name: string
  amount: string
  mode: PaymentMode
  paid_at?: string
  void_reason: string
  voided_at: string | null
  replaces_receipt: string | null
  replaces_receipt_number: string | null
  replaced_by: { id: string; receipt_number: string } | null
  pending_void_request: { id: string; reason: string } | null
  snapshot: ReceiptSnapshot
  logo_url: string | null
  created_at?: string
  created_by_name?: string | null
}

export interface PublicReceipt {
  receipt_number: string
  status: 'issued' | 'void'
  issued_at: string
  language: string
  snapshot: ReceiptSnapshot
  logo_url: string | null
}

export interface ReceiptShareLink {
  share_url: string
  expires_at: string
  whatsapp_text: string
  whatsapp_url: string
}

export interface VoidRequest {
  id: string
  receipt: string
  receipt_number: string
  payer_name: string
  amount: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  requested_by_name: string
  decided_by_name: string | null
  decided_at: string | null
  decision_note: string
  created_at: string
}

export interface CollectorAssignment {
  id: string
  event: string
  collector: string
  collector_name: string
  person: string
  person_name: string
  person_mobile: string
  person_area: string
  is_active: boolean
  active_from: string
  active_to: string | null
}

export interface CollectorPerformance {
  membership: string
  name: string
  role: string
  assigned: number
  payments: number
  total: string
  cash: string
  upi: string
  other: string
}

export interface CollectorDashboard {
  today: string
  this_week: string
  this_month: string
  total: string
  by_mode: { cash: string; upi: string; other: string }
  assigned: number
  paid_this_month: number
  pending_payments: number
  recent_receipts: { id: string; receipt_number: string; payer_name: string; amount: string; issued_at: string }[]
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

// --- Phase 4: expenses, other income, reports, audit -------------------------------------------------------
export type ExpenseStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'void'
export type IncomeSource = 'donation_box' | 'sponsorship' | 'interest' | 'sale' | 'other'

export interface ExpenseCategory {
  id: string
  name: string
  is_default: boolean
  is_active: boolean
  created_at: string
}

export interface ExpenseAttachment {
  id: string
  original_name: string
  content_type: string
  size_bytes: number
  created_at: string
}

export interface Expense {
  id: string
  event: string
  event_name: string
  financial_year: string
  category: string
  category_name: string
  amount: string
  expense_date: string
  expense_time: string | null
  mode: PaymentMode
  payee: string
  description: string
  reference_number: string
  status: ExpenseStatus
  created_by: string | null
  created_by_name: string | null
  submitted_by: string | null
  submitted_by_name: string | null
  submitted_at: string | null
  decided_by: string | null
  decided_by_name: string | null
  decided_at: string | null
  rejection_reason: string
  void_reason: string
  voided_by_name: string | null
  voided_at: string | null
  attachments: ExpenseAttachment[]
  created_at: string
  updated_at: string
}

export type ExpenseInput = Pick<Expense, 'event' | 'category' | 'amount' | 'expense_date' | 'mode' | 'payee' | 'description' | 'reference_number'> & {
  expense_time?: string | null
}

export interface OtherIncome {
  id: string
  event: string
  financial_year: string
  fund: string | null
  fund_name: string | null
  source: IncomeSource
  amount: string
  received_on: string
  mode: PaymentMode
  reference_number: string
  description: string
  status: 'recorded' | 'void'
  void_reason: string
  voided_by_name: string | null
  voided_at: string | null
  created_by_name: string | null
  created_at: string
}

export type OtherIncomeInput = Pick<OtherIncome, 'event' | 'fund' | 'source' | 'amount' | 'received_on' | 'mode' | 'reference_number' | 'description'>

export type ReportGroup = 'general' | 'financial' | 'audit'
export type ReportFilterKey =
  | 'event' | 'financial_year' | 'date_from' | 'date_to' | 'fund' | 'contribution_type' | 'collector' | 'person'
  | 'category' | 'mode' | 'status' | 'action'

export interface ReportInfo {
  type: string
  title: string
  group: ReportGroup
  filters: ReportFilterKey[]
  needs_event: boolean
  can_export: boolean
}

export interface ReportColumn {
  key: string
  label: string
  kind: 'text' | 'money' | 'number' | 'date' | 'datetime'
}

export interface ReportData {
  type: string
  title: string
  scope: string
  columns: ReportColumn[]
  rows: Record<string, string | number | null>[]
  row_count: number
  truncated: boolean
  totals: Record<string, string | number>
  notes: string[]
}

export type ExportFormat = 'csv' | 'xlsx' | 'pdf'

export interface ExportJob {
  id: string
  report_type: string
  format: ExportFormat
  status: 'pending' | 'running' | 'done' | 'failed'
  file_name: string
  row_count: number | null
  error: string
  created_at: string
  finished_at: string | null
  download_url: string | null
}

export interface AuditEntry {
  id: number
  action: string
  entity_type: string
  entity_id: string
  actor_user: string | null
  actor_name: string | null
  actor_role_code: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  changed_fields: string[]
  ip: string | null
  user_agent: string
  request_id: string
  created_at: string
}

// --- Phase 5: member portal, notifications, online payments ---------------------------------------
export interface AppNotification {
  id: string
  type: string
  title: string
  body: string
  link: string
  organization: string | null
  organization_name: string | null
  read_at: string | null
  created_at: string
}

export interface PortalMe {
  person: { id: string; full_name: string; mobile: string; email: string; address: string }
  organization: { id: string; name: string; currency: string }
  events: { id: string; name: string; status: EventStatus }[]
  online_payments: boolean
}

export interface PortalDue {
  contribution_type: string
  name: string
  event: string
  event_id: string
  expected: string
  paid: string
  due: string
}

export interface PortalSummary {
  total_paid: string
  payments: number
  by_event: { id: string; name: string; total: string }[]
  by_type: { id: string; name: string; event: string; total: string }[]
  dues: PortalDue[]
  total_due: string
}

export interface CheckoutOptions {
  provider: 'razorpay'
  key: string
  order_id: string
  amount: number
  currency: string
  name: string
  description: string
  prefill: { name: string; contact: string; email: string }
}

export interface GatewaySettings {
  provider: 'razorpay'
  key_id: string
  is_active: boolean
  has_key_secret: boolean
  has_webhook_secret: boolean
  webhook_url: string
}

export interface ReminderResult {
  notified: number
  already_reminded: number
  whatsapp: { person: string; name: string; mobile: string; due: string; whatsapp_url: string }[]
}

export interface EventFinance {
  event: { id: string; name: string; status: EventStatus }
  financial_year: { id: string; label: string }
  collection: string
  other_income: string
  approved_expenses: string
  pending_expenses: string
  rejected_expenses: string
  balance: string
}

export interface FinancialSummary {
  organization: { id: string; name: string }
  events: EventFinance[]
  total: Omit<EventFinance, 'event' | 'financial_year'>
}

export interface PlatformSummary {
  organizations: { total: number; active: number; suspended: number }
  users: number
  people: number
  receipts: number
}

export interface PlatformOrganization {
  id: string
  name: string
  city: string
  state: string
  phone: string
  email: string
  status: 'active' | 'suspended' | 'closed'
  logo_url: string | null
  created_at: string
  users_count: number
  people_count: number
  events_count: number
  receipts_count: number
  admins: { id: string; full_name: string; username: string | null; email: string | null; mobile: string | null }[]
  new_login?: boolean
}

export interface PlatformUser {
  id: string
  full_name: string
  username: string | null
  email: string | null
  mobile: string | null
  is_active: boolean
  is_platform_admin: boolean
  is_verified: boolean
  last_login: string | null
  date_joined: string
  organizations: { id: string; name: string; role: { code: string; name: string }; status: Member['status'] }[]
}

export interface LoginDetailsInput {
  full_name: string
  username?: string
  email?: string
  mobile?: string
  password: string
}

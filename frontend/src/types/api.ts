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

export interface DashboardSummary {
  events: { total: number; active: number }
  people?: { total: number; active: number }
  members?: { total: number }
  current_financial_year: { id: string; label: string } | null
  financial: null | Record<string, unknown>
  event?: { id: string; name: string; status: EventStatus; target_amount: string | null; participants: number | null }
}

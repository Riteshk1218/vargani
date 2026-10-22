import type {
  FinancialYear,
  Invitation,
  InvitationPreview,
  Member,
  MyOrganization,
  MyOrganizationDetail,
  Organization,
  OrganizationSettings,
  Paginated,
  Role,
} from '../types/api'
import { api } from './apiClient'

export type OrganizationInput = Partial<Omit<Organization, 'id' | 'slug' | 'logo_url' | 'status' | 'created_at' | 'updated_at' | 'currency'>> & {
  financial_year?: { label: string; start_date: string; end_date: string }
}

export const organizationService = {
  mine: () => api.get<MyOrganization[]>('/me/organizations/').then((r) => r.data),
  myDetail: (orgId: string) => api.get<MyOrganizationDetail>(`/me/organizations/${orgId}/`).then((r) => r.data),
  create: (input: OrganizationInput) => api.post<Organization>('/organizations/', input).then((r) => r.data),
  update: (orgId: string, input: OrganizationInput) =>
    api.patch<Organization>(`/organizations/${orgId}/`, input).then((r) => r.data),
  uploadLogo: (orgId: string, file: Blob, filename: string) => {
    const form = new FormData()
    form.append('logo', file, filename)
    return api.put<Organization>(`/organizations/${orgId}/logo/`, form).then((r) => r.data)
  },
  removeLogo: (orgId: string) => api.delete<Organization>(`/organizations/${orgId}/logo/`).then((r) => r.data),
  settings: (orgId: string) => api.get<OrganizationSettings>(`/organizations/${orgId}/settings/`).then((r) => r.data),
  updateSettings: (orgId: string, input: Partial<OrganizationSettings>) =>
    api.patch<OrganizationSettings>(`/organizations/${orgId}/settings/`, input).then((r) => r.data),
}

export const financialYearService = {
  list: () => api.get<Paginated<FinancialYear>>('/financial-years/', { params: { page_size: 100 } }).then((r) => r.data),
  create: (input: Pick<FinancialYear, 'label' | 'start_date' | 'end_date'>) =>
    api.post<FinancialYear>('/financial-years/', input).then((r) => r.data),
  update: (id: string, input: Partial<Pick<FinancialYear, 'label' | 'start_date' | 'end_date'>>) =>
    api.patch<FinancialYear>(`/financial-years/${id}/`, input).then((r) => r.data),
  setCurrent: (id: string) => api.post<FinancialYear>(`/financial-years/${id}/set-current/`).then((r) => r.data),
  close: (id: string) => api.post<FinancialYear>(`/financial-years/${id}/close/`).then((r) => r.data),
}

export const memberService = {
  list: (params: { page?: number; search?: string; page_size?: number }) =>
    api.get<Paginated<Member>>('/members/', { params }).then((r) => r.data),
  update: (id: string, input: { role_id?: string; status?: Member['status']; can_download?: boolean | null }) =>
    api.patch<Member>(`/members/${id}/`, input).then((r) => r.data),
  roles: () => api.get<Role[]>('/roles/').then((r) => r.data),
  invitations: (params: { status?: string }) =>
    api.get<Paginated<Invitation>>('/invitations/', { params }).then((r) => r.data),
  invite: (input: { full_name?: string; email?: string; mobile?: string; role_id: string }) =>
    api.post<Invitation>('/invitations/', input).then((r) => r.data),
  revokeInvitation: (id: string) => api.post<Invitation>(`/invitations/${id}/revoke/`).then((r) => r.data),
  previewInvitation: (token: string) =>
    api.get<InvitationPreview>(`/invitations/preview/${encodeURIComponent(token)}/`).then((r) => r.data),
  acceptInvitation: (token: string) =>
    api.post<MyOrganization>('/invitations/accept/', { token }).then((r) => r.data),
}

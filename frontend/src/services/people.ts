import type { Paginated, Person, PersonType } from '../types/api'
import { api } from './apiClient'

export type PersonInput = Partial<Omit<Person, 'id' | 'is_active' | 'has_login' | 'linked_user' | 'linked_user_name' | 'created_at' | 'created_by_name' | 'updated_at'>>

export const peopleService = {
  list: (params: { page?: number; search?: string; person_type?: PersonType | ''; ordering?: string; page_size?: number; date_from?: string; date_to?: string }) =>
    api.get<Paginated<Person>>('/people/', { params }).then((r) => r.data),
  get: (id: string) => api.get<Person>(`/people/${id}/`).then((r) => r.data),
  create: (input: PersonInput) => api.post<Person>('/people/', input).then((r) => r.data),
  update: (id: string, input: PersonInput) => api.patch<Person>(`/people/${id}/`, input).then((r) => r.data),
  archive: (id: string) => api.post<Person>(`/people/${id}/archive/`).then((r) => r.data),
  linkUser: (id: string, user: string) => api.post<Person>(`/people/${id}/link-user/`, { user }).then((r) => r.data),
  unlinkUser: (id: string) => api.post<Person>(`/people/${id}/unlink-user/`).then((r) => r.data),
  checkDuplicates: (mobile: string) =>
    api
      .get<{ results: { id: string; full_name: string; mobile: string }[] }>('/people/check-duplicates/', { params: { mobile } })
      .then((r) => r.data.results),
}

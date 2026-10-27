import type { EventItem, EventParticipant, EventTemplate, Paginated } from '../types/api'
import { api } from './apiClient'

export type EventInput = Partial<
  Pick<EventItem, 'name' | 'template' | 'code' | 'financial_year' | 'start_date' | 'end_date' | 'modules' | 'target_amount' | 'description' | 'thank_you_message'>
>

export const eventService = {
  list: (params: { financial_year?: string; status?: string; search?: string; page?: number; page_size?: number; ordering?: string; date_from?: string; date_to?: string }) =>
    api.get<Paginated<EventItem>>('/events/', { params }).then((r) => r.data),
  get: (id: string) => api.get<EventItem>(`/events/${id}/`).then((r) => r.data),
  create: (input: EventInput) => api.post<EventItem>('/events/', input).then((r) => r.data),
  update: (id: string, input: EventInput) => api.patch<EventItem>(`/events/${id}/`, input).then((r) => r.data),
  transition: (id: string, action: 'close' | 'reopen' | 'activate' | 'archive') =>
    api.post<EventItem>(`/events/${id}/${action}/`).then((r) => r.data),
  /** Organization Admin only: the event disappears from every list and summary. */
  remove: (id: string) => api.delete(`/events/${id}/`),
  templates: () => api.get<EventTemplate[]>('/event-templates/').then((r) => r.data),
  participants: (event: string, params: { page?: number; search?: string }) =>
    api.get<Paginated<EventParticipant>>('/event-participants/', { params: { event, ...params } }).then((r) => r.data),
  addParticipant: (input: { event: string; person: string; participation_role: EventParticipant['participation_role'] }) =>
    api.post<EventParticipant>('/event-participants/', input).then((r) => r.data),
  updateParticipant: (id: string, input: Partial<Pick<EventParticipant, 'participation_role' | 'status' | 'notes'>>) =>
    api.patch<EventParticipant>(`/event-participants/${id}/`, input).then((r) => r.data),
}

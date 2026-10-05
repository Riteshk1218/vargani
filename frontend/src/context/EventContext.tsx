import { useQuery } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { eventService } from '../services/events'
import { session } from '../services/session'
import type { EventItem } from '../types/api'
import { useOrg } from './OrgContext'

interface EventValue {
  events: EventItem[]
  activeEvent: EventItem | null
  setActiveEventId: (id: string | null) => void
  loading: boolean
}

const EventContext = createContext<EventValue | null>(null)

export function EventProvider({ children }: { children: ReactNode }) {
  const { activeOrgId, detail, can } = useOrg()
  const financialYearId = detail?.current_financial_year?.id
  const [activeEventId, setActiveEventIdState] = useState<string | null>(null)

  const eventsQuery = useQuery({
    queryKey: ['org', activeOrgId, 'events', 'switcher', financialYearId ?? 'all'],
    queryFn: () => eventService.list({ financial_year: financialYearId, page_size: 100 }),
    enabled: Boolean(activeOrgId && detail && can('events.view')),
  })
  const events = useMemo(() => (eventsQuery.data?.results ?? []).filter((e) => e.status !== 'archived'), [eventsQuery.data])

  useEffect(() => {
    if (!activeOrgId) return
    setActiveEventIdState(session.read(session.eventKey(activeOrgId)))
  }, [activeOrgId])

  const setActiveEventId = useCallback(
    (id: string | null) => {
      if (activeOrgId) session.write(session.eventKey(activeOrgId), id)
      setActiveEventIdState(id)
    },
    [activeOrgId],
  )

  const activeEvent = useMemo(() => {
    const chosen = events.find((e) => e.id === activeEventId)
    return chosen ?? events.find((e) => e.status === 'active') ?? events[0] ?? null
  }, [events, activeEventId])

  const value = useMemo(() => ({ events, activeEvent, setActiveEventId, loading: eventsQuery.isLoading }), [events, activeEvent, setActiveEventId, eventsQuery.isLoading])
  return <EventContext.Provider value={value}>{children}</EventContext.Provider>
}

export function useEvents() {
  const context = useContext(EventContext)
  if (!context) throw new Error('useEvents must be used inside EventProvider')
  return context
}

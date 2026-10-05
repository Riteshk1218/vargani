import { CalendarDays } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useEvents } from '../../context/EventContext'

export function EventSwitcher() {
  const { t } = useTranslation()
  const { events, activeEvent, setActiveEventId } = useEvents()
  if (events.length === 0) return null
  return (
    <label className="flex min-w-0 items-center gap-2 rounded-lg bg-white px-2 ring-1 ring-slate-200">
      <CalendarDays className="size-4 shrink-0 text-slate-400" aria-hidden />
      <span className="sr-only">{t('topbar.event')}</span>
      <select
        value={activeEvent?.id ?? ''}
        onChange={(e) => setActiveEventId(e.target.value)}
        className="h-9 min-w-0 max-w-[14rem] truncate border-0 bg-transparent py-0 pl-0 pr-7 text-sm font-medium focus:ring-0"
      >
        {events.map((event) => (
          <option key={event.id} value={event.id}>
            {event.name}
            {event.status === 'closed' ? ` (${t('status.closed')})` : ''}
          </option>
        ))}
      </select>
    </label>
  )
}

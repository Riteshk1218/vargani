import { useQuery } from '@tanstack/react-query'
import { CalendarPlus, Pencil } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput } from '../../components/ui/Field'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { eventService } from '../../services/events'
import { formatDate, formatMoney } from '../../utils/format'
import type { EventItem, EventStatus } from '../../types/api'
import { EventFormModal } from './EventFormModal'
import { DownloadMenu } from '../../components/DownloadMenu'
import { CreatedMeta, ListTools, useListTools } from '../../components/ListTools'
import { BulkDeleteBar, DELETE_PERMISSION, SelectBox, useRowSelection } from '../../components/BulkDelete'

export const STATUS_TONE: Record<EventStatus, 'green' | 'gray' | 'amber' | 'red'> = { active: 'green', draft: 'amber', closed: 'gray', archived: 'gray' }

export function EventsPage() {
  const { t } = useTranslation()
  const { activeOrgId, can, detail } = useOrg()
  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const tools = useListTools('-start_date', () => setPage(1))
  const [editing, setEditing] = useState<EventItem | null>(null)
  const creating = params.get('new') === '1'
  const events = useQuery({
    queryKey: ['org', activeOrgId, 'events', 'list', status, tools.query, page],
    queryFn: () => eventService.list({ status: status || undefined, ...tools.query, page }),
  })
  const canManage = can('events.manage')
  const canDelete = can(DELETE_PERMISSION)
  const selection = useRowSelection([status, tools.query])
  const closeForm = () => {
    setEditing(null)
    if (creating) setParams((prev) => (prev.delete('new'), prev))
  }

  return (
    <div>
      <PageHeader
        title={t('events.title')}
        description={t('events.subtitle')}
        actions={
          <>
            <DownloadMenu path="/events/" params={{ status, ...tools.query }} />
            {canManage && (
              <Button icon={<CalendarPlus className="size-4" />} onClick={() => setParams((prev) => (prev.set('new', '1'), prev))}>
                {t('events.create')}
              </Button>
            )}
          </>
        }
      />
      <Card>
        <div className="flex flex-wrap gap-3 border-b border-slate-200 p-4">
          <SelectInput label={t('common.status')} value={status} onChange={(e) => (setStatus(e.target.value), setPage(1))} className="w-44">
            <option value="">{t('common.all')}</option>
            {(['active', 'draft', 'closed', 'archived'] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.${s}`)}
              </option>
            ))}
          </SelectInput>
        </div>
        <ListTools
          tools={tools}
          dateLabel={t('list.addedOn')}
          sortOptions={[
            { field: 'start_date', label: t('list.startDate') },
            { field: 'end_date', label: t('list.endDate') },
            { field: 'name', label: t('list.name') },
            { field: 'created_at', label: t('list.createdAt') },
            { field: 'target_amount', label: t('events.target') },
          ]}
        />
        {events.isLoading ? (
          <SkeletonRows />
        ) : events.isError ? (
          <ErrorState onRetry={() => void events.refetch()} />
        ) : events.data!.count === 0 ? (
          <EmptyState
            icon={<CalendarPlus className="size-6" />}
            title={t('events.emptyTitle')}
            message={t('events.emptyMessage')}
            action={canManage && <Button onClick={() => setParams({ new: '1' })}>{t('events.create')}</Button>}
          />
        ) : (
          <>
            {canDelete && (
              <BulkDeleteBar selection={selection} ids={events.data!.results.map((e) => e.id)} path="/events/" invalidate={[['events'], ['dashboard']]} />
            )}
            <ul className="divide-y divide-slate-100">
              {events.data!.results.map((event) => (
                <li key={event.id} className="flex flex-col gap-2 px-4 py-3 hover:bg-slate-50 sm:flex-row sm:items-center">
                  {canDelete && <SelectBox checked={selection.has(event.id)} onChange={() => selection.toggle(event.id)} label={t('bulk.select')} />}
                  <Link to={`/app/events/${event.id}`} className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 font-medium text-slate-900">
                      <span className="truncate">{event.name}</span>
                      <Badge tone={STATUS_TONE[event.status]}>{t(`status.${event.status}`)}</Badge>
                    </p>
                    <p className="text-sm text-slate-500">
                      {event.code} · {event.financial_year_label}
                      {event.start_date && ` · ${formatDate(event.start_date)}`}
                      {event.target_amount && ` · ${t('events.target')}: ${formatMoney(event.target_amount, detail?.organization.currency)}`}
                    </p>
                    <CreatedMeta at={event.created_at} by={event.created_by_name} />
                  </Link>
                  {canManage && (
                    <Button variant="ghost" size="sm" icon={<Pencil className="size-4" />} onClick={() => setEditing(event)}>
                      {t('common.edit')}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={25} count={events.data!.count} onChange={setPage} />
          </>
        )}
      </Card>
      <EventFormModal open={creating || Boolean(editing)} event={editing} onClose={closeForm} />
    </div>
  )
}

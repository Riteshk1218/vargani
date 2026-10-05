import { useMutation, useQuery } from '@tanstack/react-query'
import { FileSpreadsheet, FileText, FileDown, BarChart3 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { exportReport, reportService } from '../../services/accounts'
import { toApiError } from '../../services/apiClient'
import { saveBlob } from '../../services/finance'
import type { ExportFormat, ReportColumn, ReportGroup, ReportInfo } from '../../types/api'
import { cn } from '../../utils/cn'
import { formatDate, formatDateTime, formatMoney } from '../../utils/format'
import { EXPENSE_STATUSES } from '../../utils/payments'

const GROUPS: ReportGroup[] = ['financial', 'general', 'audit']
const ALL_EVENTS = '__year__'

export function ReportsPage() {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const { type } = useParams()
  const reports = useQuery({ queryKey: ['org', activeOrgId, 'reports'], queryFn: reportService.list })
  const current = reports.data?.find((r) => r.type === type)

  return (
    <div>
      <PageHeader title={t('reports.title')} description={t('reports.subtitle')} />
      <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
        <Card className="h-fit print:hidden">
          {reports.isLoading ? (
            <SkeletonRows rows={6} />
          ) : reports.isError ? (
            <ErrorState onRetry={() => void reports.refetch()} />
          ) : (
            <nav aria-label={t('reports.title')} className="p-2">
              {GROUPS.map((group) => {
                const items = reports.data!.filter((r) => r.group === group)
                if (items.length === 0) return null
                return (
                  <div key={group} className="mb-2">
                    <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t(`reports.groups.${group}`)}</p>
                    <ul>
                      {items.map((r) => (
                        <li key={r.type}>
                          <Link
                            to={`/app/reports/${r.type}`}
                            className={cn('block rounded-md px-2 py-1.5 text-sm', r.type === type ? 'bg-brand-50 font-medium text-brand-800' : 'text-slate-700 hover:bg-slate-100')}
                          >
                            {r.title}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </nav>
          )}
        </Card>
        {current ? (
          <ReportViewer key={current.type} info={current} />
        ) : (
          <Card>
            <EmptyState icon={<BarChart3 className="size-6" />} title={t('reports.pick')} message={t('reports.pickMessage')} />
          </Card>
        )}
      </div>
    </div>
  )
}

function ReportViewer({ info }: { info: ReportInfo }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const { events, activeEvent } = useEvents()
  const { notify } = useToast()
  const usesEvent = info.filters.includes('event')
  // Follows the event chosen at the top of the app until the user picks another one here.
  const [eventChoice, setEventId] = useState<string | null>(null)
  const eventId = eventChoice ?? activeEvent?.id ?? (info.needs_event ? '' : ALL_EVENTS)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [status, setStatus] = useState('')
  const filters: Record<string, string | undefined> = {
    event: usesEvent && eventId && eventId !== ALL_EVENTS ? eventId : undefined,
    date_from: info.filters.includes('date_from') ? dateFrom || undefined : undefined,
    date_to: info.filters.includes('date_to') ? dateTo || undefined : undefined,
    status: info.filters.includes('status') ? status || undefined : undefined,
  }
  const ready = !info.needs_event || Boolean(filters.event)
  const report = useQuery({
    queryKey: ['org', activeOrgId, 'report', info.type, filters],
    queryFn: () => reportService.get(info.type, filters),
    enabled: ready,
  })
  const exporter = useMutation({
    mutationFn: async (format: ExportFormat) => {
      const { blob, name } = await exportReport(info.type, format, filters)
      saveBlob(blob, name)
    },
    onSuccess: () => notify(t('reports.exported')),
    onError: (error) => notify(toApiError(error).message || t('reports.exportFailed'), 'error'),
  })
  const currency = detail?.organization.currency
  const data = report.data
  const statusOptions = info.type === 'expenses' ? [...EXPENSE_STATUSES, 'all'] : info.type === 'receipts' ? ['issued', 'void'] : []

  return (
    <Card>
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">{info.title}</h2>
            {data && <p className="text-sm text-slate-500">{data.scope}</p>}
          </div>
          {info.can_export && (
            <div className="flex flex-wrap gap-2 print:hidden">
              <Button size="sm" variant="secondary" icon={<FileSpreadsheet className="size-4" />} loading={exporter.isPending && exporter.variables === 'xlsx'} disabled={!ready || exporter.isPending} onClick={() => exporter.mutate('xlsx')}>
                Excel
              </Button>
              <Button size="sm" variant="secondary" icon={<FileText className="size-4" />} loading={exporter.isPending && exporter.variables === 'pdf'} disabled={!ready || exporter.isPending} onClick={() => exporter.mutate('pdf')}>
                PDF
              </Button>
              <Button size="sm" variant="secondary" icon={<FileDown className="size-4" />} loading={exporter.isPending && exporter.variables === 'csv'} disabled={!ready || exporter.isPending} onClick={() => exporter.mutate('csv')}>
                CSV
              </Button>
            </div>
          )}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 print:hidden">
          {usesEvent && (
            <SelectInput label={t('reports.event')} value={eventId} onChange={(e) => setEventId(e.target.value)}>
              {info.needs_event ? <option value="">{t('common.choose')}</option> : <option value={ALL_EVENTS}>{t('reports.allEventsInYear')}</option>}
              {events.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </SelectInput>
          )}
          {info.filters.includes('date_from') && <TextInput label={t('reports.from')} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />}
          {info.filters.includes('date_to') && <TextInput label={t('reports.to')} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />}
          {statusOptions.length > 0 && (
            <SelectInput label={t('common.status')} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">{info.type === 'expenses' ? t('expenseStatus.approved') : t('common.all')}</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? t('common.all') : s === 'issued' ? t('receipts.status.issued') : t(`expenseStatus.${s}`)}
                </option>
              ))}
            </SelectInput>
          )}
        </div>
      </div>
      {!ready ? (
        <EmptyState title={t('common.selectEvent')} message={t('reports.needsEvent')} />
      ) : report.isLoading ? (
        <SkeletonRows />
      ) : report.isError ? (
        <ErrorState message={toApiError(report.error).message} onRetry={() => void report.refetch()} />
      ) : data!.rows.length === 0 ? (
        <EmptyState icon={<BarChart3 className="size-6" />} title={t('reports.noRows')} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  {data!.columns.map((c) => (
                    <th key={c.key} scope="col" className={cn('whitespace-nowrap px-3 py-2 font-medium', numeric(c) && 'text-right')}>
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data!.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    {data!.columns.map((c) => (
                      <td key={c.key} className={cn('px-3 py-2', numeric(c) ? 'whitespace-nowrap text-right tabular-nums' : 'max-w-xs')}>
                        {cell(row[c.key], c, currency)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-2 border-t border-slate-200 p-4 text-sm">
            {data!.truncated && <p className="text-amber-700">{t('reports.truncated', { shown: data!.rows.length, total: data!.row_count })}</p>}
            <dl className="ml-auto grid w-full max-w-sm grid-cols-[1fr_auto] gap-x-4 gap-y-1">
              {Object.entries(data!.totals).map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="text-slate-600">{totalLabel(key, data!.columns, t)}</dt>
                  <dd className="text-right font-semibold tabular-nums">{key === 'count' || typeof value === 'number' ? value : formatMoney(String(value), currency)}</dd>
                </div>
              ))}
            </dl>
            {data!.notes.map((note) => (
              <p key={note} className="text-xs text-slate-500">
                {note}
              </p>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}

function numeric(c: ReportColumn) {
  return c.kind === 'money' || c.kind === 'number'
}

function cell(value: string | number | null | undefined, column: ReportColumn, currency?: string) {
  if (value === null || value === undefined || value === '') return <span className="text-slate-300">—</span>
  if (column.kind === 'money') return formatMoney(String(value), currency)
  if (column.kind === 'date') return formatDate(String(value))
  if (column.kind === 'datetime') return formatDateTime(String(value))
  return value
}

function totalLabel(key: string, columns: ReportColumn[], t: (k: string, o?: Record<string, string>) => string) {
  const column = columns.find((c) => c.key === key)
  if (column) return t('reports.totalOf', { label: column.label })
  if (key === 'count') return t('reports.rows')
  if (key === 'balance') return t('dashboard.balance')
  return key
}

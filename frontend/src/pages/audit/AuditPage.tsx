import { useQuery } from '@tanstack/react-query'
import { ChevronDown, History } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { auditService } from '../../services/accounts'
import type { AuditEntry } from '../../types/api'
import { cn } from '../../utils/cn'
import { formatDateTime } from '../../utils/format'
import { DownloadMenu } from '../../components/DownloadMenu'

const ACTIONS = [
  'create', 'update', 'status_change', 'soft_delete', 'approve', 'reject', 'void', 'expense_submit', 'receipt_issue',
  'void_request', 'void_approve', 'void_reject', 'login', 'login_failed', 'role_change', 'permission_change', 'invite', 'export',
]

/** Who changed what, and when. Read-only: audit entries can never be edited or deleted. */
export function AuditPage() {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const [action, setAction] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)
  const params = {
    action: action || undefined,
    date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
    date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
    page,
  }
  const entries = useQuery({ queryKey: ['org', activeOrgId, 'audit', params], queryFn: () => auditService.list(params) })

  return (
    <div>
      <PageHeader title={t('audit.title')} description={t('audit.subtitle')} actions={<DownloadMenu path="/audit-logs/" params={params} />} />
      <Card>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-3">
          <SelectInput label={t('audit.action')} value={action} onChange={(e) => (setAction(e.target.value), setPage(1))}>
            <option value="">{t('common.all')}</option>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {actionLabel(a, t)}
              </option>
            ))}
          </SelectInput>
          <TextInput label={t('reports.from')} type="date" value={dateFrom} onChange={(e) => (setDateFrom(e.target.value), setPage(1))} />
          <TextInput label={t('reports.to')} type="date" value={dateTo} onChange={(e) => (setDateTo(e.target.value), setPage(1))} />
        </div>
        {entries.isLoading ? (
          <SkeletonRows />
        ) : entries.isError ? (
          <ErrorState onRetry={() => void entries.refetch()} />
        ) : entries.data!.count === 0 ? (
          <EmptyState icon={<History className="size-6" />} title={t('audit.empty')} />
        ) : (
          <>
            <ul className="divide-y divide-slate-100">
              {entries.data!.results.map((entry) => (
                <li key={entry.id}>
                  <button
                    type="button"
                    aria-expanded={open === entry.id}
                    onClick={() => setOpen(open === entry.id ? null : entry.id)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate">
                        <span className="font-medium">{entry.actor_name ?? t('audit.system')}</span> · {actionLabel(entry.action, t)} · {entityLabel(entry.entity_type, t)}
                      </p>
                      <p className="truncate text-slate-500">
                        {formatDateTime(entry.created_at)}
                        {entry.actor_role_code && ` · ${t(`roles.${entry.actor_role_code}`, { defaultValue: entry.actor_role_code })}`}
                        {entry.ip && ` · ${entry.ip}`}
                      </p>
                    </div>
                    <ChevronDown className={cn('size-4 shrink-0 text-slate-400 transition', open === entry.id && 'rotate-180')} aria-hidden />
                  </button>
                  {open === entry.id && <AuditChanges entry={entry} />}
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={25} count={entries.data!.count} onChange={setPage} />
          </>
        )}
      </Card>
    </div>
  )
}

function AuditChanges({ entry }: { entry: AuditEntry }) {
  const { t } = useTranslation()
  const before = entry.before ?? {}
  const after = entry.after ?? {}
  const keys = entry.changed_fields.length > 0 ? entry.changed_fields : Object.keys({ ...before, ...after })
  return (
    <div className="bg-slate-50 px-4 pb-4 text-xs">
      <p className="mb-2 text-slate-500">
        {t('audit.record')}: <span className="font-mono">{entry.entity_id}</span>
      </p>
      {keys.length === 0 ? (
        <p className="text-slate-500">{t('audit.noDetails')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">{t('audit.field')}</th>
                <th className="py-1 pr-3 font-medium">{t('audit.before')}</th>
                <th className="py-1 font-medium">{t('audit.after')}</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key} className="align-top">
                  <td className="py-1 pr-3 font-mono text-slate-600">{key}</td>
                  <td className="max-w-xs break-words py-1 pr-3 text-red-700">{show(before[key])}</td>
                  <td className="max-w-xs break-words py-1 text-emerald-700">{show(after[key])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function show(value: unknown) {
  if (value === undefined || value === null || value === '') return '—'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function actionLabel(action: string, t: (k: string, o?: Record<string, string>) => string) {
  return t(`audit.actions.${action}`, { defaultValue: action.replace(/_/g, ' ') })
}

function entityLabel(entity: string, t: (k: string, o?: Record<string, string>) => string) {
  const name = entity.split('.').pop() ?? entity
  return t(`audit.entities.${name}`, { defaultValue: name })
}

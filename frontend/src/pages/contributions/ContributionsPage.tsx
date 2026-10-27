import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { HandCoins, Search, Users, Wallet } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useApiErrors } from '../../hooks/useApiErrors'
import { Badge, Card, PageHeader, StatCard } from '../../components/ui/Card'
import { BarList } from '../../components/ui/BarList'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useDebounced } from '../../hooks/useDebounced'
import { contributionService, contributionTypeService, dueService } from '../../services/finance'
import type { Due } from '../../types/api'
import { formatDate, formatMobile, formatMoney, formatMonth, formatStamp } from '../../utils/format'
import { cn } from '../../utils/cn'
import { DownloadMenu } from '../../components/DownloadMenu'
import { CreatedMeta, ListTools, useListTools } from '../../components/ListTools'
import { RemindButton } from './RemindButton'

type Tab = 'list' | 'balances' | 'dues'

export function ContributionsPage() {
  const { t } = useTranslation()
  const { activeEvent } = useEvents()
  const { scope } = useOrg()
  const [tab, setTab] = useState<Tab>('list')
  const [, setParams] = useSearchParams()
  // Each tab has its own sort fields and dates, so a new tab starts from its defaults.
  const openTab = (value: Tab) => {
    setTab(value)
    setParams({}, { replace: true })
  }

  if (!activeEvent) {
    return (
      <div>
        <PageHeader title={t('contributions.title')} />
        <Card>
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        </Card>
      </div>
    )
  }
  const showDues = scope('contributions.view') === 'all'
  const tabs: Tab[] = showDues ? ['list', 'balances', 'dues'] : ['list', 'balances']
  return (
    <div>
      <PageHeader title={t('contributions.title')} description={`${activeEvent.name} · ${t('contributions.subtitle')}`} />
      <Summary eventId={activeEvent.id} />
      {(
        <div className="mb-3 mt-6 flex gap-1 border-b border-slate-200" role="tablist">
          {tabs.map((value) => (
            <button
              key={value}
              role="tab"
              aria-selected={tab === value}
              onClick={() => openTab(value)}
              className={cn('-mb-px border-b-2 px-3 py-2 text-sm font-medium', tab === value ? 'border-brand-700 text-brand-800' : 'border-transparent text-slate-500 hover:text-slate-800')}
            >
              {t(`contributions.tab.${value}`)}
            </button>
          ))}
        </div>
      )}
      <div>
        {tab === 'list' ? <ContributionList eventId={activeEvent.id} /> : tab === 'balances' ? <Balances eventId={activeEvent.id} /> : <Dues eventId={activeEvent.id} />}
      </div>
    </div>
  )
}

function Summary({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const currency = detail?.organization.currency
  const summary = useQuery({ queryKey: ['org', activeOrgId, 'contributions', 'summary', eventId], queryFn: () => contributionService.summary(eventId) })
  if (summary.isLoading) return <SkeletonRows rows={2} />
  if (summary.isError) return <ErrorState onRetry={() => void summary.refetch()} />
  const s = summary.data!
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label={t('contributions.collected')} value={formatMoney(s.collected, currency)} hint={s.target_amount ? t('dashboard.ofTarget', { target: formatMoney(s.target_amount, currency) }) : undefined} icon={<Wallet className="size-5" />} />
        <StatCard label={t('contributions.contributors')} value={s.contributors} icon={<Users className="size-5" />} />
        <StatCard label={t('contributions.payments')} value={s.payments} icon={<HandCoins className="size-5" />} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('contributions.byType')}</h2>
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={s.by_type.map((r) => ({ label: r.name, value: r.total }))} />
        </Card>
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('contributions.byMode')}</h2>
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={s.by_mode.map((r) => ({ label: t(`mode.${r.mode}`), value: r.total }))} />
        </Card>
      </div>
    </div>
  )
}

function ContributionList({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const tools = useListTools('-contributed_on', () => setPage(1))
  const debounced = useDebounced(search)
  const types = useQuery({ queryKey: ['org', activeOrgId, 'contribution-types', eventId], queryFn: () => contributionTypeService.list(eventId) })
  const rows = useQuery({
    queryKey: ['org', activeOrgId, 'contributions', 'list', eventId, debounced, type, tools.query, page],
    queryFn: () => contributionService.list({ event: eventId, search: debounced || undefined, contribution_type: type || undefined, ...tools.query, page }),
  })
  const currency = detail?.organization.currency
  return (
    <Card>
      <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[1fr_14rem_auto] sm:items-end">
        <div className="relative">
          <TextInput label={t('common.search')} placeholder={t('people.searchPlaceholder')} value={search} onChange={(e) => (setSearch(e.target.value), setPage(1))} />
          <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
        </div>
        <SelectInput label={t('collect.type')} value={type} onChange={(e) => (setType(e.target.value), setPage(1))}>
          <option value="">{t('common.all')}</option>
          {(types.data?.results ?? []).map((ct) => (
            <option key={ct.id} value={ct.id}>
              {ct.name}
            </option>
          ))}
        </SelectInput>
        <DownloadMenu path="/contributions/" params={{ event: eventId, search: debounced, contribution_type: type, ...tools.query }} />
      </div>
      <ListTools
        tools={tools}
        sortOptions={[
          { field: 'contributed_on', label: t('common.date') },
          { field: 'created_at', label: t('list.createdAt') },
          { field: 'amount', label: t('common.amount') },
          { field: 'person__full_name', label: t('collect.person') },
          { field: 'period_month', label: t('list.forMonth') },
        ]}
      />
      {rows.isLoading ? (
        <SkeletonRows />
      ) : rows.isError ? (
        <ErrorState onRetry={() => void rows.refetch()} />
      ) : rows.data!.count === 0 ? (
        <EmptyState title={t('contributions.empty')} message={t('contributions.emptyMessage')} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2 font-medium">{t('collect.person')}</th>
                  <th className="hidden px-4 py-2 font-medium sm:table-cell">{t('collect.type')}</th>
                  <th className="hidden px-4 py-2 font-medium md:table-cell">{t('common.date')}</th>
                  <th className="hidden px-4 py-2 font-medium lg:table-cell">{t('list.createdAt')}</th>
                  <th className="hidden px-4 py-2 font-medium lg:table-cell">{t('list.createdBy')}</th>
                  <th className="px-4 py-2 text-right font-medium">{t('common.amount')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.data!.results.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3">
                      <p className="font-medium">{c.person_name}</p>
                      <p className="text-xs text-slate-500 sm:hidden">
                        {c.contribution_type_name}
                        {c.period_month && ` · ${formatMonth(c.period_month)}`}
                      </p>
                      <CreatedMeta at={c.created_at} by={c.created_by_name} className="text-xs text-slate-500 lg:hidden" />
                    </td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      {c.contribution_type_name}
                      {c.period_month && <span className="text-slate-500"> · {formatMonth(c.period_month)}</span>}
                    </td>
                    <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{formatDate(c.contributed_on)}</td>
                    <td className="hidden whitespace-nowrap px-4 py-3 text-slate-600 lg:table-cell">{formatStamp(c.created_at)}</td>
                    <td className="hidden px-4 py-3 text-slate-600 lg:table-cell">{c.created_by_name ?? '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="tabular-nums">{formatMoney(c.amount, currency)}</span>
                      {c.status !== 'confirmed' && (
                        <span className="ml-2">
                          <Badge tone={c.status === 'pending' ? 'amber' : 'gray'}>{t(`lineStatus.${c.status}`)}</Badge>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={25} count={rows.data!.count} onChange={setPage} />
        </>
      )}
    </Card>
  )
}

function Dues({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const currency = detail?.organization.currency
  const types = useQuery({
    queryKey: ['org', activeOrgId, 'contribution-types', eventId, 'mandatory'],
    queryFn: () => contributionTypeService.list(eventId, { is_mandatory: true }),
  })
  const [chosen, setChosen] = useState('')
  const typeId = chosen || types.data?.results[0]?.id || ''
  const report = useQuery({
    queryKey: ['org', activeOrgId, 'contributions', 'dues', typeId],
    queryFn: () => contributionTypeService.outstanding(typeId),
    enabled: Boolean(typeId),
  })

  if (types.isLoading) return <SkeletonRows rows={2} />
  if ((types.data?.results.length ?? 0) === 0) {
    return (
      <Card>
        <EmptyState title={t('contributions.noMandatory')} message={t('contributions.noMandatoryMessage')} />
      </Card>
    )
  }
  const r = report.data
  return (
    <Card>
      <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[16rem_1fr] sm:items-end">
        <SelectInput label={t('collect.type')} value={typeId} onChange={(e) => setChosen(e.target.value)}>
          {types.data!.results.map((ct) => (
            <option key={ct.id} value={ct.id}>
              {ct.name}
            </option>
          ))}
        </SelectInput>
        {r && (
          <div className="flex flex-wrap items-center gap-3 sm:justify-end">
            <p className="text-sm text-slate-600 sm:text-right">
              {t('contributions.duesSummary', {
                due: formatMoney(r.total_due, currency),
                count: r.people_with_dues,
                expected: formatMoney(r.expected_per_person, currency),
              })}
            </p>
            {r.people_with_dues > 0 && <RemindButton contributionTypeId={typeId} />}
          </div>
        )}
      </div>
      {report.isLoading ? (
        <SkeletonRows />
      ) : report.isError ? (
        <ErrorState onRetry={() => void report.refetch()} />
      ) : r!.results.length === 0 ? (
        <EmptyState title={t('contributions.noParticipants')} message={t('contributions.noParticipantsMessage')} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">{t('collect.person')}</th>
                <th className="hidden px-4 py-2 text-right font-medium sm:table-cell">{t('contributions.expected')}</th>
                <th className="px-4 py-2 text-right font-medium">{t('contributions.paid')}</th>
                <th className="px-4 py-2 text-right font-medium">{t('contributions.due')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {r!.results.map((row) => (
                <tr key={row.person}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.person_name}</p>
                    <p className="text-xs text-slate-500">{formatMobile(row.mobile)}</p>
                  </td>
                  <td className="hidden px-4 py-3 text-right tabular-nums sm:table-cell">{formatMoney(row.expected, currency)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatMoney(row.paid, currency)}</td>
                  <td className={cn('px-4 py-3 text-right font-medium tabular-nums', Number(row.due) > 0 ? 'text-red-700' : 'text-emerald-700')}>
                    {formatMoney(row.due, currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

/** Balances (baaki): receipts given before all of the money came, and what is still owed. */
function Balances({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const currency = detail?.organization.currency
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [writeOff, setWriteOff] = useState<Due | null>(null)
  const tools = useListTools('-created_at', () => setPage(1))
  const debounced = useDebounced(search)
  const params = { event: eventId, open: true, search: debounced || undefined, ...tools.query, page }
  const dues = useQuery({ queryKey: ['org', activeOrgId, 'dues', 'list', params], queryFn: () => dueService.list(params) })
  const cancel = useMutation({
    mutationFn: (due: Due) => dueService.cancel(due.id, t('balances.writtenOffReason')),
    onSuccess: async () => {
      setWriteOff(null)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'dues'] })
      notify(t('balances.writtenOff'))
    },
    onError,
  })
  const canCollect = can('payments.create')
  return (
    <Card>
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <TextInput label={t('common.search')} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} placeholder={t('collect.searchPerson')} />
          <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
        </div>
        <DownloadMenu path="/dues/" params={{ event: eventId, open: true, search: debounced || undefined, ...tools.query }} />
      </div>
      <ListTools
        tools={tools}
        sortOptions={[
          { field: 'created_at', label: t('list.createdAt') },
          { field: 'remaining', label: t('balances.stillOwed') },
          { field: 'amount', label: t('balances.balance') },
          { field: 'person__full_name', label: t('collect.person') },
        ]}
      />
      {dues.isLoading ? (
        <SkeletonRows />
      ) : dues.isError ? (
        <ErrorState onRetry={() => void dues.refetch()} />
      ) : dues.data!.count === 0 ? (
        <EmptyState title={t('balances.none')} message={t('balances.noneMessage')} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">{t('collect.person')}</th>
                <th className="hidden px-4 py-2 font-medium sm:table-cell">{t('collect.type')}</th>
                <th className="hidden px-4 py-2 text-right font-medium md:table-cell">{t('balances.balance')}</th>
                <th className="px-4 py-2 text-right font-medium">{t('balances.stillOwed')}</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dues.data!.results.map((due) => (
                <tr key={due.id}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{due.person_name}</p>
                    <p className="text-xs text-slate-500">{[formatMobile(due.person_mobile), due.receipt_number].filter(Boolean).join(' · ')}</p>
                    <CreatedMeta at={due.created_at} by={due.created_by_name} />
                  </td>
                  <td className="hidden px-4 py-3 sm:table-cell">
                    {due.contribution_type_name}
                    {due.period_month && <span className="text-slate-500"> · {formatMonth(due.period_month)}</span>}
                  </td>
                  <td className="hidden px-4 py-3 text-right tabular-nums md:table-cell">{formatMoney(due.amount, currency)}</td>
                  <td className="px-4 py-3 text-right font-medium tabular-nums text-red-700">{formatMoney(due.remaining, currency)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {canCollect && (
                        <Link to={`/app/collect?person=${due.person}`}>
                          <Button size="sm" variant="secondary">{t('collect.collectBalance')}</Button>
                        </Link>
                      )}
                      {can('records.admin_edit') && (
                        <Button size="sm" variant="ghost" onClick={() => setWriteOff(due)}>
                          {t('balances.writeOff')}
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pageSize={25} count={dues.data?.count ?? 0} onChange={setPage} />
      <ConfirmDialog
        open={Boolean(writeOff)}
        title={t('balances.writeOffTitle')}
        message={writeOff ? t('balances.writeOffMessage', { name: writeOff.person_name, amount: formatMoney(writeOff.remaining, currency) }) : ''}
        confirmLabel={t('balances.writeOff')}
        danger
        loading={cancel.isPending}
        onConfirm={() => writeOff && cancel.mutate(writeOff)}
        onClose={() => setWriteOff(null)}
      />
    </Card>
  )
}

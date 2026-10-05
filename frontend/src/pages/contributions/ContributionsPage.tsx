import { useQuery } from '@tanstack/react-query'
import { HandCoins, Search, Users, Wallet } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge, Card, PageHeader, StatCard } from '../../components/ui/Card'
import { BarList } from '../../components/ui/BarList'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useDebounced } from '../../hooks/useDebounced'
import { contributionService, contributionTypeService } from '../../services/finance'
import { formatDate, formatMobile, formatMoney, formatMonth } from '../../utils/format'
import { cn } from '../../utils/cn'

type Tab = 'list' | 'dues'

export function ContributionsPage() {
  const { t } = useTranslation()
  const { activeEvent } = useEvents()
  const { scope } = useOrg()
  const [tab, setTab] = useState<Tab>('list')

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
  return (
    <div>
      <PageHeader title={t('contributions.title')} description={`${activeEvent.name} · ${t('contributions.subtitle')}`} />
      <Summary eventId={activeEvent.id} />
      {showDues && (
        <div className="mb-3 mt-6 flex gap-1 border-b border-slate-200" role="tablist">
          {(['list', 'dues'] as Tab[]).map((value) => (
            <button
              key={value}
              role="tab"
              aria-selected={tab === value}
              onClick={() => setTab(value)}
              className={cn('-mb-px border-b-2 px-3 py-2 text-sm font-medium', tab === value ? 'border-brand-700 text-brand-800' : 'border-transparent text-slate-500 hover:text-slate-800')}
            >
              {t(`contributions.tab.${value}`)}
            </button>
          ))}
        </div>
      )}
      <div className={cn(!showDues && 'mt-6')}>{tab === 'list' ? <ContributionList eventId={activeEvent.id} /> : <Dues eventId={activeEvent.id} />}</div>
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
  const debounced = useDebounced(search)
  const types = useQuery({ queryKey: ['org', activeOrgId, 'contribution-types', eventId], queryFn: () => contributionTypeService.list(eventId) })
  const rows = useQuery({
    queryKey: ['org', activeOrgId, 'contributions', 'list', eventId, debounced, type, page],
    queryFn: () => contributionService.list({ event: eventId, search: debounced || undefined, contribution_type: type || undefined, page }),
  })
  const currency = detail?.organization.currency
  return (
    <Card>
      <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[1fr_14rem]">
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
      </div>
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
                    </td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      {c.contribution_type_name}
                      {c.period_month && <span className="text-slate-500"> · {formatMonth(c.period_month)}</span>}
                    </td>
                    <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{formatDate(c.contributed_on)}</td>
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
          <p className="text-sm text-slate-600 sm:text-right">
            {t('contributions.duesSummary', {
              due: formatMoney(r.total_due, currency),
              count: r.people_with_dues,
              expected: formatMoney(r.expected_per_person, currency),
            })}
          </p>
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

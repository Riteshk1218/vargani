import { useQuery } from '@tanstack/react-query'
import { Scale } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput } from '../../components/ui/Field'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { financeService } from '../../services/finance'
import { financialYearService } from '../../services/organizations'
import type { EventFinance } from '../../types/api'
import { formatMoney } from '../../utils/format'

/** Collection − Approved expenses = Balance, one card per event, for one financial year of this mandal. */
export function FinancialSummaryPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const currency = detail?.organization.currency
  const years = useQuery({ queryKey: ['org', activeOrgId, 'financial-years'], queryFn: financialYearService.list })
  const [yearId, setYearId] = useState('')
  useEffect(() => {
    const list = years.data?.results ?? []
    if (!yearId && list.length) setYearId((list.find((y) => y.is_current) ?? list[0]).id)
  }, [years.data, yearId])
  const summary = useQuery({
    queryKey: ['org', activeOrgId, 'finance-summary', yearId],
    queryFn: () => financeService.summary({ financial_year: yearId }),
    enabled: Boolean(yearId),
  })

  return (
    <div>
      <PageHeader title={t('finance.title')} description={`${detail?.organization.name ?? ''} · ${t('finance.subtitle')}`} />
      <Card className="mb-4 p-4">
        <SelectInput className="sm:w-64" label={t('finance.financialYear')} value={yearId} onChange={(e) => setYearId(e.target.value)}>
          {years.data?.results.map((y) => (
            <option key={y.id} value={y.id}>
              {y.label}
            </option>
          ))}
        </SelectInput>
      </Card>
      {summary.isLoading || years.isLoading ? (
        <Card>
          <SkeletonRows rows={3} />
        </Card>
      ) : summary.isError ? (
        <Card>
          <ErrorState onRetry={() => void summary.refetch()} />
        </Card>
      ) : !summary.data || summary.data.events.length === 0 ? (
        <Card>
          <EmptyState icon={<Scale className="size-6" />} title={t('finance.empty')} />
        </Card>
      ) : (
        <div className="space-y-4">
          {summary.data.events.map((row) => (
            <EventCard key={row.event.id} row={row} currency={currency} />
          ))}
          {summary.data.events.length > 1 && (
            <Card className="p-4">
              <h2 className="mb-2 font-semibold">{t('finance.allEvents', { label: summary.data.events[0].financial_year.label })}</h2>
              <Totals values={summary.data.total} currency={currency} />
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

function EventCard({ row, currency }: { row: EventFinance; currency?: string }) {
  const { t } = useTranslation()
  return (
    <Card className="p-4" >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">{row.event.name}</h2>
          <p className="text-sm text-slate-500">{t('finance.fy', { label: row.financial_year.label })}</p>
        </div>
        <Badge tone={row.event.status === 'active' ? 'green' : 'gray'}>{t(`status.${row.event.status}`)}</Badge>
      </div>
      <Totals values={row} currency={currency} />
      {(Number(row.pending_expenses) > 0 || Number(row.rejected_expenses) > 0) && (
        <p className="mt-3 text-sm text-slate-500">
          {t('finance.notCounted', { pending: formatMoney(row.pending_expenses, currency), rejected: formatMoney(row.rejected_expenses, currency) })}{' '}
          <Link className="font-medium text-brand-700 underline" to="/app/expenses">
            {t('finance.openExpenses')}
          </Link>
        </p>
      )}
    </Card>
  )
}

function Totals({ values, currency }: { values: Omit<EventFinance, 'event' | 'financial_year'>; currency?: string }) {
  const { t } = useTranslation()
  const hasOther = Number(values.other_income) > 0
  const negative = values.balance.startsWith('-')
  return (
    <dl className="grid gap-1 text-sm" data-testid="finance-totals">
      <div className="flex justify-between">
        <dt>{t('finance.collection')}</dt>
        <dd className="tabular-nums">{formatMoney(values.collection, currency)}</dd>
      </div>
      {hasOther && (
        <div className="flex justify-between">
          <dt>+ {t('finance.otherIncome')}</dt>
          <dd className="tabular-nums">{formatMoney(values.other_income, currency)}</dd>
        </div>
      )}
      <div className="flex justify-between">
        <dt>− {t('finance.approvedExpenses')}</dt>
        <dd className="tabular-nums">{formatMoney(values.approved_expenses, currency)}</dd>
      </div>
      <div className="mt-1 flex justify-between border-t border-slate-200 pt-2 text-base font-semibold">
        <dt>= {t('finance.balance')}</dt>
        <dd className={negative ? 'tabular-nums text-red-700' : 'tabular-nums text-emerald-700'}>{formatMoney(values.balance, currency)}</dd>
      </div>
    </dl>
  )
}

import { useQuery } from '@tanstack/react-query'
import { CalendarDays, CalendarPlus, HandCoins, IndianRupee, ShieldCheck, UserPlus, Users, Wallet } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { BarList } from '../../components/ui/BarList'
import { Card, PageHeader, StatCard } from '../../components/ui/Card'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { dashboardService } from '../../services/dashboard'
import type { FinancialSummary } from '../../types/api'
import { formatDateTime, formatMoney, formatMonth } from '../../utils/format'

export function DashboardPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  const summary = useQuery({
    queryKey: ['org', activeOrgId, 'dashboard', activeEvent?.id ?? 'none'],
    queryFn: () => dashboardService.summary(activeEvent?.id),
  })

  const org = detail!.organization
  return (
    <div>
      <PageHeader title={t('dashboard.title')} description={activeEvent ? t('dashboard.forEvent', { event: activeEvent.name }) : org.name} />
      {summary.isLoading ? (
        <Card>
          <SkeletonRows rows={3} />
        </Card>
      ) : summary.isError ? (
        <Card>
          <ErrorState onRetry={() => void summary.refetch()} />
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <StatCard label={t('dashboard.events')} value={summary.data!.events.total} hint={t('dashboard.activeCount', { count: summary.data!.events.active })} icon={<CalendarDays className="size-5" />} />
            {summary.data!.people && (
              <StatCard label={t('dashboard.people')} value={summary.data!.people.total} hint={t('dashboard.activeCount', { count: summary.data!.people.active })} icon={<Users className="size-5" />} />
            )}
            {summary.data!.members && <StatCard label={t('dashboard.users')} value={summary.data!.members.total} icon={<ShieldCheck className="size-5" />} />}
            {activeEvent?.target_amount && !summary.data!.financial && (
              <StatCard label={t('dashboard.target')} value={formatMoney(activeEvent.target_amount, org.currency)} icon={<IndianRupee className="size-5" />} />
            )}
          </div>

          {summary.data!.financial &&
            (summary.data!.financial.payments === 0 && summary.data!.financial.pending_payments === 0 ? (
              <Card>
                <EmptyState
                  icon={<IndianRupee className="size-6" />}
                  title={t('dashboard.noCollectionsTitle')}
                  message={t('dashboard.noCollectionsMessage')}
                  action={
                    can('payments.create') &&
                    activeEvent && (
                      <Link to="/app/collect">
                        <Button icon={<HandCoins className="size-4" />}>{t('collect.title')}</Button>
                      </Link>
                    )
                  }
                />
              </Card>
            ) : (
              <FinancialSection financial={summary.data!.financial} currency={org.currency} />
            ))}

          {summary.data!.events.total === 0 && can('events.manage') && (
            <Card>
              <EmptyState
                icon={<CalendarPlus className="size-6" />}
                title={t('dashboard.firstEventTitle')}
                message={t('dashboard.firstEventMessage')}
                action={
                  <Link to="/app/events?new=1">
                    <Button icon={<CalendarPlus className="size-4" />}>{t('events.create')}</Button>
                  </Link>
                }
              />
            </Card>
          )}
          {summary.data!.people?.total === 0 && can('people.manage') && (
            <Card>
              <EmptyState
                icon={<UserPlus className="size-6" />}
                title={t('dashboard.firstPersonTitle')}
                message={t('dashboard.firstPersonMessage')}
                action={
                  <Link to="/app/people?new=1">
                    <Button icon={<UserPlus className="size-4" />}>{t('people.add')}</Button>
                  </Link>
                }
              />
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

function FinancialSection({ financial, currency }: { financial: FinancialSummary; currency: string }) {
  const { t } = useTranslation()
  const percent =
    financial.target_amount && Number(financial.target_amount) > 0
      ? Math.min(100, Math.round((Number(financial.collected) / Number(financial.target_amount)) * 100))
      : null
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          label={t('dashboard.collected')}
          value={formatMoney(financial.collected, currency)}
          hint={financial.target_amount ? t('dashboard.ofTarget', { target: formatMoney(financial.target_amount, currency) }) : undefined}
          icon={<Wallet className="size-5" />}
        />
        <StatCard label={t('contributions.contributors')} value={financial.contributors} icon={<Users className="size-5" />} />
        <StatCard
          label={t('contributions.payments')}
          value={financial.payments}
          hint={financial.pending_payments ? t('dashboard.pendingCount', { count: financial.pending_payments }) : undefined}
          icon={<HandCoins className="size-5" />}
        />
        <StatCard label={t('dashboard.balance')} value={formatMoney(financial.balance, currency)} hint={t('dashboard.balanceHint')} icon={<IndianRupee className="size-5" />} />
      </div>
      {percent !== null && (
        <Card className="p-4">
          <div className="mb-2 flex justify-between text-sm">
            <span className="font-medium">{t('dashboard.targetProgress')}</span>
            <span className="tabular-nums text-slate-600">{percent}%</span>
          </div>
          <div className="h-3 rounded-full bg-slate-100" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-3 rounded-full bg-brand-600" style={{ width: `${percent}%` }} />
          </div>
        </Card>
      )}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('dashboard.byMonth')}</h2>
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={financial.by_month.map((r) => ({ label: formatMonth(r.month), value: r.total }))} />
        </Card>
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('contributions.byMode')}</h2>
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={financial.by_mode.map((r) => ({ label: t(`mode.${r.mode}`), value: r.total }))} />
        </Card>
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('contributions.byFund')}</h2>
          <BarList
            currency={currency}
            emptyLabel={t('contributions.noneYet')}
            items={financial.by_fund.map((r) => ({ label: r.name ?? t('ctypes.noFund'), value: r.total }))}
          />
        </Card>
      </div>
      <Card>
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold">{t('dashboard.recent')}</h2>
          <Link to="/app/payments" className="text-sm font-medium text-brand-700 hover:underline">
            {t('dashboard.viewAll')}
          </Link>
        </div>
        <ul className="divide-y divide-slate-100">
          {financial.recent_payments.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="truncate font-medium">{p.payer_name}</p>
                <p className="truncate text-slate-500">
                  {formatDateTime(p.paid_at)} · {t(`mode.${p.mode}`)}
                  {p.receipt_number && ` · ${p.receipt_number}`}
                </p>
              </div>
              <span className="shrink-0 font-semibold tabular-nums">{formatMoney(p.amount, currency)}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

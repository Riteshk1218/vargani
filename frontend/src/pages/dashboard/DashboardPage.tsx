import { useQuery } from '@tanstack/react-query'
import { AlarmClock, BadgeCheck, CalendarClock, CalendarDays, CalendarPlus, HandCoins, IndianRupee, Receipt, ShieldCheck, UserPlus, Users, Wallet } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'
import { AnnouncementButton } from '../../components/AnnouncementButton'
import { Button } from '../../components/ui/Button'
import { BarList } from '../../components/ui/BarList'
import { Card, PageHeader, StatCard } from '../../components/ui/Card'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { ListTools, useListTools } from '../../components/ListTools'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { dashboardService } from '../../services/dashboard'
import { CollectorDashboard } from './CollectorDashboard'
import type { DashboardSummary, FinancialSummary } from '../../types/api'
import { formatMoney, formatMonth, formatStamp } from '../../utils/format'

export function DashboardPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  // ?date_from=&date_to= : pick a day (e.g. 27 Oct) to see what was collected, spent and still owed on it.
  const days = useListTools('')
  const summary = useQuery({
    queryKey: ['org', activeOrgId, 'dashboard', activeEvent?.id ?? 'none', days.dateFrom, days.dateTo],
    queryFn: () => dashboardService.summary(activeEvent?.id, days.dateFrom || undefined, days.dateTo || undefined),
  })
  /** The same days on the list a card opens, so its numbers match the card. */
  const withDays = (path: string) => withDates(path, days.dateFrom, days.dateTo)

  const org = detail!.organization
  // Members only see their own contributions.
  if (detail!.role.code === 'member' && detail!.member_portal_enabled) return <Navigate to="/app/my" replace />
  return (
    <div>
      <PageHeader
        title={t('dashboard.title')}
        description={activeEvent ? t('dashboard.forEvent', { event: activeEvent.name }) : org.name}
        actions={can('notifications.send') && <AnnouncementButton />}
      />
      {(summary.data?.financial || summary.data?.follow_ups) && (
        <Card className="mb-6">
          <ListTools tools={days} dateLabel={t('dashboard.dateFilter')} className="p-4" />
          {days.filtered && <p className="px-4 pb-3 text-xs text-slate-500">{t('dashboard.dateFilterHint')}</p>}
        </Card>
      )}
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
            <StatCard to="/app/events" testId="card-events" label={t('dashboard.events')} value={summary.data!.events.total} hint={t('dashboard.activeCount', { count: summary.data!.events.active })} icon={<CalendarDays className="size-5" />} />
            {summary.data!.people && (
              <StatCard to="/app/people" testId="card-people" label={t('dashboard.people')} value={summary.data!.people.total} hint={t('dashboard.activeCount', { count: summary.data!.people.active })} icon={<Users className="size-5" />} />
            )}
            {summary.data!.members && <StatCard to={can('members.view') ? '/app/users' : undefined} testId="card-users" label={t('dashboard.users')} value={summary.data!.members.total} icon={<ShieldCheck className="size-5" />} />}
            {activeEvent?.target_amount && !summary.data!.financial && (
              <StatCard to={`/app/events/${activeEvent.id}`} label={t('dashboard.target')} value={formatMoney(activeEvent.target_amount, org.currency)} icon={<IndianRupee className="size-5" />} />
            )}
          </div>

          {summary.data!.follow_ups && <FollowUpCards followUps={summary.data!.follow_ups} currency={org.currency} withDays={withDays} />}

          {!summary.data!.financial && activeEvent && can('collectors.view_performance') && <CollectorDashboard eventId={activeEvent.id} />}

          {summary.data!.financial &&
            (summary.data!.financial.payments === 0 && summary.data!.financial.pending_payments === 0 && !days.filtered ? (
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
              <FinancialSection financial={summary.data!.financial} currency={org.currency} withDays={withDays} />
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

/** Door-to-door follow-up: pavtis to visit. Each card opens the matching list of pavtis. */
function FollowUpCards({ followUps, currency, withDays }: { followUps: NonNullable<DashboardSummary['follow_ups']>; currency: string; withDays: (path: string) => string }) {
  const { t } = useTranslation()
  const cards = [
    { key: 'overdue', to: '/app/payments?follow_up=overdue', label: t('pavti.overdue'), value: followUps.overdue, tone: followUps.overdue > 0 ? 'text-red-700' : 'text-slate-900', icon: <AlarmClock className="size-5" />, hint: t('pavti.overdueHint') },
    { key: 'today', to: '/app/payments?follow_up=today', label: t('pavti.dueToday'), value: followUps.due_today, tone: followUps.due_today > 0 ? 'text-amber-700' : 'text-slate-900', icon: <CalendarClock className="size-5" />, hint: t('pavti.dueTodayHint') },
    { key: 'owing', to: '/app/payments?pavti=owing', label: t('pavti.owingAll'), value: followUps.owing, tone: 'text-slate-900', icon: <HandCoins className="size-5" />, hint: t('pavti.stillOwed', { amount: formatMoney(followUps.balance, currency) }) },
    ...(followUps.paid !== undefined
      ? [{ key: 'paid', to: '/app/payments?pavti=paid', label: t('pavti.paidAll'), value: followUps.paid, tone: 'text-emerald-700', icon: <BadgeCheck className="size-5" />, hint: t('pavti.paidAllHint') }]
      : []),
  ]
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <StatCard key={card.key} to={withDays(card.to)} testId={`follow-up-${card.key}`} label={card.label} value={card.value} tone={card.tone} icon={card.icon} hint={card.hint} />
      ))}
    </div>
  )
}

/** Add ?date_from=&date_to= to a list link. */
function withDates(path: string, from: string, to: string) {
  if (!from && !to) return path
  const [base, query = ''] = path.split('?')
  const params = new URLSearchParams(query)
  if (from) params.set('date_from', from)
  if (to) params.set('date_to', to)
  return `${base}?${params.toString()}`
}

/** First and last day of a "2026-10" month. */
function monthRange(month: string) {
  const [year, m] = month.split('-').map(Number)
  const last = new Date(year, m, 0).getDate()
  return { from: `${month}-01`, to: `${month}-${String(last).padStart(2, '0')}` }
}

function FinancialSection({ financial, currency, withDays }: { financial: FinancialSummary; currency: string; withDays: (path: string) => string }) {
  const { t } = useTranslation()
  const { can } = useOrg()
  const financeLink = can('dashboard.view_financial') || can('reports.view_financial') ? '/app/finance' : undefined
  const percent =
    financial.target_amount && Number(financial.target_amount) > 0
      ? Math.min(100, Math.round((Number(financial.collected) / Number(financial.target_amount)) * 100))
      : null
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          to={withDays('/app/payments?status=successful')}
          testId="card-collected"
          label={t('dashboard.collected')}
          value={formatMoney(financial.collected, currency)}
          hint={financial.target_amount ? t('dashboard.ofTarget', { target: formatMoney(financial.target_amount, currency) }) : undefined}
          icon={<Wallet className="size-5" />}
        />
        <StatCard
          to={can('expenses.view') ? withDays('/app/expenses?status=approved') : undefined}
          testId="card-expenses"
          label={t('dashboard.expenses')}
          value={formatMoney(financial.expenses, currency)}
          hint={financial.pending_expenses ? t('dashboard.waitingApproval', { count: financial.pending_expenses }) : undefined}
          icon={<Receipt className="size-5" />}
        />
        <StatCard
          to={financeLink}
          testId="card-balance"
          label={t('dashboard.balance')}
          value={formatMoney(financial.balance, currency)}
          hint={t('dashboard.incomeHint', { income: formatMoney(financial.income, currency) })}
          icon={<IndianRupee className="size-5" />}
        />
        <StatCard
          to={withDays(financial.pending_payments ? '/app/payments?status=pending' : '/app/payments')}
          testId="card-payments"
          label={t('contributions.payments')}
          value={financial.payments}
          hint={
            financial.pending_payments
              ? t('dashboard.pendingCount', { count: financial.pending_payments })
              : t('dashboard.contributorsCount', { count: financial.contributors })
          }
          icon={<HandCoins className="size-5" />}
        />
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
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={financial.by_month.map((r) => {
              const range = monthRange(r.month)
              return { label: formatMonth(r.month), value: r.total, to: withDates('/app/contributions', range.from, range.to) }
            })} />
        </Card>
        <Card className="p-4">
          <h2 className="mb-3 font-semibold">{t('contributions.byMode')}</h2>
          <BarList currency={currency} emptyLabel={t('contributions.noneYet')} items={financial.by_mode.map((r) => ({ label: t(`mode.${r.mode}`), value: r.total, to: withDays(`/app/payments?status=successful&mode=${r.mode}`) }))} />
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
      {(financial.expenses_by_category.length > 0 || Number(financial.other_income) > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="p-4">
            <h2 className="mb-3 font-semibold">{t('dashboard.expensesByCategory')}</h2>
            <BarList currency={currency} emptyLabel={t('dashboard.noExpenses')} items={financial.expenses_by_category.map((r) => ({ label: r.name, value: r.total, to: can('expenses.view') ? withDays(`/app/expenses?status=approved&category=${r.id}`) : undefined }))} />
          </Card>
          <Card className="p-4">
            <h2 className="mb-3 font-semibold">{t('dashboard.incomeVsExpense')}</h2>
            <BarList
              currency={currency}
              emptyLabel={t('contributions.noneYet')}
              items={[
                { label: t('dashboard.collected'), value: financial.collected, to: withDays('/app/payments?status=successful') },
                { label: t('income.title'), value: financial.other_income, to: can('other_income.manage') ? withDays('/app/income') : undefined },
                { label: t('dashboard.expenses'), value: financial.expenses, to: can('expenses.view') ? withDays('/app/expenses?status=approved') : undefined },
              ]}
            />
          </Card>
        </div>
      )}
      <Card>
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold">{t('dashboard.recent')}</h2>
          <Link to={withDays('/app/payments')} className="text-sm font-medium text-brand-700 hover:underline">
            {t('dashboard.viewAll')}
          </Link>
        </div>
        <ul className="divide-y divide-slate-100">
          {financial.recent_payments.map((p) => (
            <li key={p.id}>
              <Link to={`/app/payments?open=${p.id}`} className="flex items-center justify-between gap-3 px-4 py-3 text-sm hover:bg-slate-50">
                <div className="min-w-0">
                  <p className="truncate font-medium">{p.payer_name}</p>
                  <p className="truncate text-slate-500">
                    {formatStamp(p.paid_at)} · {t(`mode.${p.mode}`)}
                    {p.receipt_number && ` · ${p.receipt_number}`}
                  </p>
                </div>
                <span className="shrink-0 font-semibold tabular-nums">{formatMoney(p.amount, currency)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

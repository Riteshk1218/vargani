import { useQuery } from '@tanstack/react-query'
import { CalendarDays, HandCoins, IndianRupee, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card, StatCard } from '../../components/ui/Card'
import { SkeletonRows } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { collectorService } from '../../services/finance'
import { formatDateTime, formatMoney } from '../../utils/format'

/** A karyakarta's own numbers for the selected event. */
export function CollectorDashboard({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const currency = detail?.organization.currency
  const data = useQuery({ queryKey: ['org', activeOrgId, 'collectors', 'me', eventId], queryFn: () => collectorService.myDashboard(eventId) })
  if (data.isLoading) return <SkeletonRows rows={3} />
  if (!data.data) return null
  const d = data.data
  return (
    <div className="space-y-4">
      {can('payments.create') && (
        <Link to="/app/collect" className="block">
          <Button className="w-full sm:w-auto" icon={<HandCoins className="size-4" />}>
            {t('collect.title')}
          </Button>
        </Link>
      )}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard label={t('collectors.today')} value={formatMoney(d.today, currency)} icon={<IndianRupee className="size-5" />} />
        <StatCard label={t('collectors.thisMonth')} value={formatMoney(d.this_month, currency)} icon={<CalendarDays className="size-5" />} />
        <StatCard label={t('collectors.total')} value={formatMoney(d.total, currency)} hint={`${t('mode.cash')} ${formatMoney(d.by_mode.cash, currency)} · ${t('mode.upi')} ${formatMoney(d.by_mode.upi, currency)}`} icon={<HandCoins className="size-5" />} />
        <StatCard label={t('collectors.assigned')} value={d.assigned} hint={t('collectors.paidThisMonth', { count: d.paid_this_month })} icon={<Users className="size-5" />} />
      </div>
      <Card>
        <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('collectors.recentReceipts')}</h2>
        {d.recent_receipts.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-slate-500">{t('contributions.noneYet')}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {d.recent_receipts.map((r) => (
              <li key={r.id}>
                <Link to={`/app/receipts/${r.id}`} className="flex items-center justify-between gap-3 px-4 py-3 text-sm hover:bg-slate-50">
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{r.payer_name}</span>
                    <span className="block truncate text-slate-500">
                      {r.receipt_number} · {formatDateTime(r.issued_at)}
                    </span>
                  </span>
                  <span className="shrink-0 font-semibold tabular-nums">{formatMoney(r.amount, currency)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

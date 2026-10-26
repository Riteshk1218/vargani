import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, HandCoins, Pencil } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader, StatCard } from '../../components/ui/Card'
import { SelectInput } from '../../components/ui/Field'
import { EmptyState, ErrorState, SkeletonRows, Spinner } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { paymentService } from '../../services/finance'
import { peopleService } from '../../services/people'
import type { Payment } from '../../types/api'
import { formatMobile, formatMoney, formatMonth, formatStamp, sumMoney } from '../../utils/format'
import { PAVTI_TONE, PAYMENT_TONE } from '../../utils/payments'
import { PersonFormModal } from './PersonFormModal'

const PAGE = 100

/** Every pavti of one person, across all events and years, newest first. */
async function allPayments(payer: string): Promise<Payment[]> {
  const found: Payment[] = []
  for (let page = 1; ; page += 1) {
    const data = await paymentService.list({ payer, ordering: '-paid_at', page, page_size: PAGE })
    found.push(...data.results)
    if (!data.next) return found
  }
}

export function PersonDetailPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const { activeOrgId, detail, can } = useOrg()
  const currency = detail?.organization.currency
  const [editing, setEditing] = useState(false)
  const [event, setEvent] = useState('')
  const canSeeMoney = can('payments.view')

  const person = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'detail', id],
    queryFn: () => peopleService.get(id),
  })
  const history = useQuery({
    queryKey: ['org', activeOrgId, 'payments', 'person', id],
    queryFn: () => allPayments(id),
    enabled: canSeeMoney,
  })

  const events = useMemo(() => {
    const names = new Map<string, string>()
    for (const p of history.data ?? []) names.set(p.event, p.event_name)
    return [...names.entries()]
  }, [history.data])
  const shown = useMemo(() => (history.data ?? []).filter((p) => !event || p.event === event), [history.data, event])
  const received = shown.filter((p) => p.status === 'successful')

  if (person.isLoading) return <Spinner />
  if (person.isError) return <ErrorState onRetry={() => void person.refetch()} />
  const p = person.data!
  const address = [p.unit, p.building, p.area, p.address_line, p.city, p.pincode].filter(Boolean).join(', ')

  return (
    <div>
      <Link to="/app/people" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="size-4" aria-hidden />
        {t('people.title')}
      </Link>
      <PageHeader
        title={p.full_name}
        description={[formatMobile(p.mobile), formatMobile(p.alt_mobile), address].filter(Boolean).join(' · ')}
        actions={
          <>
            {can('people.manage') && (
              <Button variant="secondary" icon={<Pencil className="size-4" />} onClick={() => setEditing(true)}>
                {t('common.edit')}
              </Button>
            )}
            {can('payments.create') && (
              <Link to={`/app/collect?person=${p.id}`}>
                <Button icon={<HandCoins className="size-4" />}>{t('collect.title')}</Button>
              </Link>
            )}
          </>
        }
      />
      {(p.person_types.length > 0 || p.notes) && (
        <div className="mb-6 space-y-2">
          <div className="flex flex-wrap gap-1">
            {p.person_types.map((pt) => (
              <Badge key={pt}>{t(`personType.${pt}`)}</Badge>
            ))}
          </div>
          {p.notes && <p className="text-sm text-slate-600">{p.notes}</p>}
        </div>
      )}

      {canSeeMoney && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t('personHistory.totalPaid')} value={formatMoney(sumMoney(received.map((r) => r.amount)), currency)} />
            <StatCard label={t('personHistory.stillOwed')} value={formatMoney(sumMoney(received.map((r) => r.balance_due)), currency)} />
            <StatCard label={t('personHistory.pavtis')} value={received.length} />
            <StatCard label={t('personHistory.lastPaid')} value={<span className="text-lg">{received[0] ? formatStamp(received[0].paid_at) : '—'}</span>} />
          </div>
          <Card>
            <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-end sm:justify-between">
              <h2 className="font-semibold text-slate-900">{t('personHistory.title')}</h2>
              {events.length > 1 && (
                <div className="sm:w-60">
                  <SelectInput label={t('personHistory.event')} value={event} onChange={(e) => setEvent(e.target.value)}>
                    <option value="">{t('common.all')}</option>
                    {events.map(([value, name]) => (
                      <option key={value} value={value}>
                        {name}
                      </option>
                    ))}
                  </SelectInput>
                </div>
              )}
            </div>
            {history.isLoading ? (
              <SkeletonRows />
            ) : history.isError ? (
              <ErrorState onRetry={() => void history.refetch()} />
            ) : shown.length === 0 ? (
              <EmptyState icon={<HandCoins className="size-6" />} title={t('personHistory.empty')} />
            ) : (
              <ul className="divide-y divide-slate-100">
                {shown.map((payment) => (
                  <HistoryRow key={payment.id} payment={payment} currency={currency} />
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
      <PersonFormModal open={editing} person={p} onClose={() => setEditing(false)} />
    </div>
  )
}

function HistoryRow({ payment, currency }: { payment: Payment; currency?: string }) {
  const { t } = useTranslation()
  const { can } = useOrg()
  const types = payment.lines
    .map((line) => (line.period_month ? `${line.contribution_type_name} (${formatMonth(line.period_month)})` : line.contribution_type_name))
    .join(', ')
  const owing = payment.status === 'successful' && payment.pavti_status && payment.pavti_status !== 'paid'
  return (
    <li className="flex items-start justify-between gap-3 px-4 py-3 text-sm">
      <div className="min-w-0">
        <p className="font-medium text-slate-900">{types || t('personHistory.contribution')}</p>
        <p className="text-slate-500">
          {formatStamp(payment.paid_at)} · {payment.event_name} · {t(`mode.${payment.mode}`)}
        </p>
        <p className="text-xs text-slate-500">
          {payment.receipt &&
            (can('receipts.view') ? (
              <Link className="font-mono text-brand-700 hover:underline" to={`/app/receipts/${payment.receipt.id}`}>
                {payment.receipt.receipt_number}
              </Link>
            ) : (
              <span className="font-mono">{payment.receipt.receipt_number}</span>
            ))}
          {payment.receipt && payment.collector_name && ' · '}
          {payment.collector_name && t('personHistory.collectedBy', { name: payment.collector_name })}
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className="font-semibold tabular-nums">{formatMoney(payment.amount, currency)}</p>
        <span className="mt-1 flex justify-end">
          {payment.status === 'successful' && payment.pavti_status ? (
            <Badge tone={PAVTI_TONE[payment.pavti_status]}>{t(`pavti.status.${payment.pavti_status}`)}</Badge>
          ) : (
            <Badge tone={PAYMENT_TONE[payment.status]}>{t(`paymentStatus.${payment.status}`)}</Badge>
          )}
        </span>
        {owing && <p className="mt-1 text-xs text-amber-700">{t('pavti.stillOwed', { amount: formatMoney(payment.balance_due, currency) })}</p>}
      </div>
    </li>
  )
}

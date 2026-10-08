import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { HandCoins, Pencil, ReceiptText, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { useDebounced } from '../../hooks/useDebounced'
import { paymentService } from '../../services/finance'
import type { Payment, PaymentStatus } from '../../types/api'
import { formatMobile, formatMoney, formatMonth, formatStamp } from '../../utils/format'
import { MANUAL_MODES, PAYMENT_TONE } from '../../utils/payments'
import { PaymentEditModal } from './PaymentEditModal'


const STATUSES: PaymentStatus[] = ['successful', 'pending', 'failed', 'cancelled', 'deleted']

export function PaymentsPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [mode, setMode] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Payment | null>(null)
  const debounced = useDebounced(search)
  const eventId = activeEvent?.id
  const payments = useQuery({
    queryKey: ['org', activeOrgId, 'payments', 'list', eventId, debounced, status, mode, page],
    queryFn: () => paymentService.list({ event: eventId, search: debounced || undefined, status: status || undefined, mode: mode || undefined, page }),
    enabled: Boolean(eventId),
  })
  const currency = detail?.organization.currency
  const filtered = Boolean(debounced || status || mode)

  return (
    <div>
      <PageHeader
        title={t('payments.title')}
        description={activeEvent ? `${activeEvent.name} · ${t('payments.subtitle')}` : t('payments.subtitle')}
        actions={
          can('payments.create') && (
            <Link to="/app/collect">
              <Button icon={<HandCoins className="size-4" />}>{t('collect.title')}</Button>
            </Link>
          )
        }
      />
      <Card>
        {!eventId ? (
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        ) : (
          <>
            <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[1fr_10rem_10rem]">
              <div className="relative">
                <TextInput label={t('common.search')} placeholder={t('payments.searchPlaceholder')} value={search} onChange={(e) => (setSearch(e.target.value), setPage(1))} />
                <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
              </div>
              <SelectInput label={t('common.status')} value={status} onChange={(e) => (setStatus(e.target.value), setPage(1))}>
                <option value="">{t('common.all')}</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {t(`paymentStatus.${s}`)}
                  </option>
                ))}
              </SelectInput>
              <SelectInput label={t('collect.mode')} value={mode} onChange={(e) => (setMode(e.target.value), setPage(1))}>
                <option value="">{t('common.all')}</option>
                {MANUAL_MODES.map((m) => (
                  <option key={m} value={m}>
                    {t(`mode.${m}`)}
                  </option>
                ))}
              </SelectInput>
            </div>
            {payments.isLoading ? (
              <SkeletonRows />
            ) : payments.isError ? (
              <ErrorState onRetry={() => void payments.refetch()} />
            ) : payments.data!.count === 0 ? (
              <EmptyState icon={<HandCoins className="size-6" />} title={filtered ? t('people.noMatches') : t('payments.empty')} message={filtered ? undefined : t('payments.emptyMessage')} />
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {payments.data!.results.map((p) => (
                    <li key={p.id}>
                      <button type="button" onClick={() => setSelected(p)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50">
                        <div className="min-w-0">
                          <p className={p.is_anonymous ? 'truncate font-medium italic text-slate-600' : 'truncate font-medium'}>{p.payer_name}</p>
                          <p className="truncate text-slate-500">
                            {formatStamp(p.paid_at)} · {t(`mode.${p.mode}`)}
                            {p.receipt && ` · ${p.receipt.receipt_number}`}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="font-semibold tabular-nums">{formatMoney(p.amount, currency)}</p>
                          <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatus.${p.status}`)}</Badge>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
                <Pagination page={page} pageSize={25} count={payments.data!.count} onChange={setPage} />
              </>
            )}
          </>
        )}
      </Card>
      <PaymentDetailModal payment={selected} onClose={() => setSelected(null)} onChanged={setSelected} />
    </div>
  )
}

type StatusAction = 'confirm' | 'cancel' | 'fail' | 'delete'

function PaymentDetailModal({ payment, onClose, onChanged }: { payment: Payment | null; onClose: () => void; onChanged: (p: Payment) => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [action, setAction] = useState<StatusAction | null>(null)
  const [reason, setReason] = useState('')
  const change = useMutation({
    mutationFn: ({ id, act }: { id: string; act: StatusAction }) =>
      act === 'delete' ? paymentService.adminDelete(id, reason) : paymentService.changeStatus(id, act, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('common.saved'))
      setAction(null)
      setReason('')
      onClose()
    },
    onError,
  })
  const [editing, setEditing] = useState(false)
  if (!payment) return null
  const currency = detail?.organization.currency
  const pending = payment.status === 'pending'
  const isAdmin = can('records.admin_edit')
  const editable = isAdmin && (payment.status === 'successful' || pending)
  if (editing) return <PaymentEditModal payment={payment} onClose={() => setEditing(false)} onSaved={(p) => (setEditing(false), onChanged(p))} />

  return (
    <Modal
      open
      title={payment.payer_name}
      onClose={onClose}
      footer={
        action ? (
          <>
            <Button variant="secondary" onClick={() => setAction(null)}>
              {t('common.back')}
            </Button>
            <Button variant={action === 'confirm' ? 'primary' : 'danger'} loading={change.isPending} onClick={() => change.mutate({ id: payment.id, act: action })}>
              {t(`payments.${action}`)}
            </Button>
          </>
        ) : (
          <>
            {editable && (
              <>
                <Button variant="ghost" icon={<Trash2 className="size-4" />} onClick={() => setAction('delete')}>
                  {t('payments.delete')}
                </Button>
                <Button variant="secondary" icon={<Pencil className="size-4" />} onClick={() => setEditing(true)}>
                  {t('common.edit')}
                </Button>
              </>
            )}
            {pending && can('payments.cancel_pending') && (
              <>
                <Button variant="ghost" onClick={() => setAction('cancel')}>
                  {t('payments.cancel')}
                </Button>
                <Button variant="ghost" onClick={() => setAction('fail')}>
                  {t('payments.fail')}
                </Button>
              </>
            )}
            {pending && can('payments.create') && <Button onClick={() => setAction('confirm')}>{t('payments.confirm')}</Button>}
            {payment.receipt && (
              <Link to={`/app/receipts/${payment.receipt.id}`}>
                <Button icon={<ReceiptText className="size-4" />}>{t('payments.viewReceipt')}</Button>
              </Link>
            )}
          </>
        )
      }
    >
      {action ? (
        <div className="space-y-3 text-sm">
          <p>{t(`payments.${action}Message`, { amount: formatMoney(payment.amount, currency), name: payment.payer_name })}</p>
          {action !== 'confirm' && <TextInput label={t('payments.reason')} value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />}
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-semibold tabular-nums">{formatMoney(payment.amount, currency)}</span>
            <Badge tone={PAYMENT_TONE[payment.status]}>{t(`paymentStatus.${payment.status}`)}</Badge>
          </div>
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1">
            <dt className="text-slate-500">{t('people.mobile')}</dt>
            <dd>{formatMobile(payment.payer_mobile) || '—'}</dd>
            <dt className="text-slate-500">{t('finance.event')}</dt>
            <dd>{payment.event_name}</dd>
            <dt className="text-slate-500">{t('finance.financialYear')}</dt>
            <dd>{payment.financial_year_label}</dd>
            <dt className="text-slate-500">{t('payments.dateTime')}</dt>
            <dd data-testid="payment-stamp">{formatStamp(payment.paid_at)}</dd>
            <dt className="text-slate-500">{t('collect.mode')}</dt>
            <dd>
              {t(`mode.${payment.mode}`)}
              {payment.reference_number && ` · ${payment.reference_number}`}
              {payment.cheque_bank && ` · ${payment.cheque_bank}`}
            </dd>
            {payment.collector_name && (
              <>
                <dt className="text-slate-500">{t('receipts.collectedBy')}</dt>
                <dd>{payment.collector_name}</dd>
              </>
            )}
            <dt className="text-slate-500">{t('receipts.number')}</dt>
            <dd className="font-mono">{payment.receipt?.receipt_number ?? t('payments.noReceipt')}</dd>
            {payment.notes && (
              <>
                <dt className="text-slate-500">{t('common.notes')}</dt>
                <dd>{payment.notes}</dd>
              </>
            )}
            {payment.status_reason && (
              <>
                <dt className="text-slate-500">{t('payments.reason')}</dt>
                <dd>{payment.status_reason}</dd>
              </>
            )}
          </dl>
          <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
            {payment.lines.map((line) => (
              <li key={line.id} className="flex justify-between px-3 py-2">
                <span>
                  {line.contribution_type_name}
                  {line.period_month && <span className="text-slate-500"> · {formatMonth(line.period_month)}</span>}
                </span>
                <span className="tabular-nums">{formatMoney(line.amount, currency)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  )
}

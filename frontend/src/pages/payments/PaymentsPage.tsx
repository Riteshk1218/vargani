import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClock, HandCoins, Pencil, ReceiptText, Search, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
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
import { formatDate, formatMobile, formatMoney, formatMonth, formatStamp } from '../../utils/format'
import { FOLLOW_UP_TONE, MANUAL_MODES, PAVTI_TONE, PAYMENT_TONE } from '../../utils/payments'
import { PaymentEditModal } from './PaymentEditModal'
import { PavtiVisitModal } from './PavtiVisitModal'
import { DownloadMenu } from '../../components/DownloadMenu'
import { CreatedMeta, ListTools, useListTools } from '../../components/ListTools'
import { BulkDeleteBar, DELETE_PERMISSION, SelectBox, useRowSelection } from '../../components/BulkDelete'


const STATUSES: PaymentStatus[] = ['successful', 'pending', 'failed', 'cancelled', 'deleted']

/** Door-to-door follow-up filters. The first four go to `follow_up`, the rest to `pavti`. */
const FOLLOW_UP_FILTERS = ['overdue', 'today', 'upcoming', 'none'] as const
const PAVTI_FILTERS = ['owing', 'unpaid', 'partly_paid', 'paid'] as const

/** The pavti's paid / partly paid / unpaid badge and, while money is owed, its follow-up date. */
export function PavtiBadges({ payment }: { payment: Payment }) {
  const { t } = useTranslation()
  if (!payment.pavti_status || payment.pavti_status === 'paid') return null
  return (
    <span className="mt-1 flex flex-wrap justify-end gap-1">
      <Badge tone={PAVTI_TONE[payment.pavti_status]}>{t(`pavti.status.${payment.pavti_status}`)}</Badge>
      {payment.follow_up_on && (
        <Badge tone={payment.follow_up_state ? FOLLOW_UP_TONE[payment.follow_up_state] : 'gray'}>
          {payment.follow_up_state === 'overdue'
            ? t('pavti.overdueSince', { date: formatDate(payment.follow_up_on) })
            : payment.follow_up_state === 'today'
              ? t('pavti.dueToday')
              : t('pavti.followUpOn', { date: formatDate(payment.follow_up_on) })}
        </Badge>
      )}
    </span>
  )
}

export function PaymentsPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  // ?follow_up=overdue, ?pavti=unpaid, ?status=, ?mode= and ?date_from=&date_to= (from the dashboard) open the
  // list already filtered; ?open=<id> opens that payment.
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState(params.get('status') ?? '')
  const [mode, setMode] = useState(params.get('mode') ?? '')
  const followUp = params.get('follow_up') ?? ''
  const pavti = params.get('pavti') ?? ''
  const pavtiFilter = followUp || pavti
  const setPavtiFilter = (value: string) => {
    const next = new URLSearchParams(params)
    next.delete('follow_up')
    next.delete('pavti')
    if ((FOLLOW_UP_FILTERS as readonly string[]).includes(value)) next.set('follow_up', value)
    else if (value) next.set('pavti', value)
    setParams(next, { replace: true })
    setPage(1)
  }
  const [page, setPage] = useState(1)
  const tools = useListTools(followUp ? 'follow_up_on' : '-paid_at', () => setPage(1))
  const [selected, setSelected] = useState<Payment | null>(null)
  const openId = params.get('open')
  useEffect(() => {
    if (!openId) return
    void paymentService.get(openId).then(setSelected, () => undefined)
    const next = new URLSearchParams(params)
    next.delete('open')
    setParams(next, { replace: true })
  }, [openId])
  const debounced = useDebounced(search)
  const eventId = activeEvent?.id
  const payments = useQuery({
    queryKey: ['org', activeOrgId, 'payments', 'list', eventId, debounced, status, mode, followUp, pavti, tools.query, page],
    queryFn: () =>
      paymentService.list({
        event: eventId,
        search: debounced || undefined,
        status: status || undefined,
        mode: mode || undefined,
        follow_up: followUp || undefined,
        pavti: pavti || undefined,
        ...tools.query,
        page,
      }),
    enabled: Boolean(eventId),
  })
  const currency = detail?.organization.currency
  const filtered = Boolean(debounced || status || mode || pavtiFilter || tools.filtered)
  const selection = useRowSelection([eventId, debounced, status, mode, followUp, pavti, tools.query])
  const canDelete = can(DELETE_PERMISSION)

  return (
    <div>
      <PageHeader
        title={t('payments.title')}
        description={activeEvent ? `${activeEvent.name} · ${t('payments.subtitle')}` : t('payments.subtitle')}
        actions={
          <>
            <DownloadMenu path="/payments/" params={{ event: eventId, search: debounced, status, mode, follow_up: followUp, pavti, ...tools.query }} />
            {can('payments.create') && (
              <Link to="/app/collect">
                <Button icon={<HandCoins className="size-4" />}>{t('collect.title')}</Button>
              </Link>
            )}
          </>
        }
      />
      <Card>
        {!eventId ? (
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        ) : (
          <>
            <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[1fr_11rem_10rem_10rem]">
              <div className="relative">
                <TextInput label={t('common.search')} placeholder={t('payments.searchPlaceholder')} value={search} onChange={(e) => (setSearch(e.target.value), setPage(1))} />
                <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
              </div>
              <SelectInput label={t('pavti.filter')} value={pavtiFilter} onChange={(e) => setPavtiFilter(e.target.value)}>
                <option value="">{t('common.all')}</option>
                {FOLLOW_UP_FILTERS.map((f) => (
                  <option key={f} value={f}>
                    {t(`pavti.filters.${f}`)}
                  </option>
                ))}
                {PAVTI_FILTERS.map((f) => (
                  <option key={f} value={f}>
                    {t(`pavti.filters.${f}`)}
                  </option>
                ))}
              </SelectInput>
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
            <ListTools
              tools={tools}
              dateLabel={t('payments.dateTime')}
              sortOptions={[
                { field: 'paid_at', label: t('payments.dateTime') },
                { field: 'created_at', label: t('list.createdAt') },
                { field: 'amount', label: t('common.amount') },
                { field: 'payer__full_name', label: t('people.fullName') },
                { field: 'balance_due', label: t('balances.stillOwed') },
                { field: 'follow_up_on', label: t('pavti.followUpDate') },
              ]}
            />
            {payments.isLoading ? (
              <SkeletonRows />
            ) : payments.isError ? (
              <ErrorState onRetry={() => void payments.refetch()} />
            ) : payments.data!.count === 0 ? (
              <EmptyState icon={<HandCoins className="size-6" />} title={filtered ? t('people.noMatches') : t('payments.empty')} message={filtered ? undefined : t('payments.emptyMessage')} />
            ) : (
              <>
                {canDelete && (
                  <BulkDeleteBar
                    selection={selection}
                    ids={payments.data!.results.filter((p) => p.status !== 'deleted').map((p) => p.id)}
                    path="/payments/"
                    invalidate={[['payments'], ['contributions'], ['receipts'], ['dues'], ['dashboard']]}
                    message={t('bulk.confirmCollections')}
                  />
                )}
                <ul className="divide-y divide-slate-100">
                  {payments.data!.results.map((p) => (
                    <li key={p.id} className="flex items-center">
                      {canDelete && (
                        <SelectBox className="ml-4" checked={selection.has(p.id)} onChange={() => selection.toggle(p.id)} label={t('bulk.select')} />
                      )}
                      <button type="button" onClick={() => setSelected(p)} className="flex min-w-0 flex-1 items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50">
                        <div className="min-w-0">
                          <p className={p.is_anonymous ? 'truncate font-medium italic text-slate-600' : 'truncate font-medium'}>{p.payer_name}</p>
                          <p className="truncate text-slate-500">
                            {formatStamp(p.paid_at)} · {t(`mode.${p.mode}`)}
                            {p.receipt && ` · ${p.receipt.receipt_number}`}
                          </p>
                          <CreatedMeta at={p.created_at} by={p.created_by_name} />
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="font-semibold tabular-nums">{formatMoney(p.amount, currency)}</p>
                          {p.pavti_status && p.pavti_status !== 'paid' ? (
                            <PavtiBadges payment={p} />
                          ) : (
                            <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatus.${p.status}`)}</Badge>
                          )}
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
  const [visiting, setVisiting] = useState(false)
  if (!payment) return null
  const currency = detail?.organization.currency
  const pending = payment.status === 'pending'
  const isAdmin = can('records.admin_edit')
  const editable = isAdmin && (payment.status === 'successful' || pending)
  if (editing) return <PaymentEditModal payment={payment} onClose={() => setEditing(false)} onSaved={(p) => (setEditing(false), onChanged(p))} />
  if (visiting) return <PavtiVisitModal payment={payment} onClose={() => setVisiting(false)} onSaved={(p) => (setVisiting(false), onChanged(p))} />
  const owing = payment.status === 'successful' && Number(payment.balance_due) > 0

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
            {owing && can('payments.create') && (
              <Button icon={<CalendarClock className="size-4" />} onClick={() => setVisiting(true)}>
                {t('pavti.update')}
              </Button>
            )}
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
          {owing && (
            <div className="rounded-lg bg-amber-50 p-3 text-amber-900 ring-1 ring-amber-200">
              <p className="font-semibold">{t('pavti.stillOwed', { amount: formatMoney(payment.balance_due, currency) })}</p>
              <p>{payment.follow_up_on ? t('pavti.followUpOn', { date: formatDate(payment.follow_up_on) }) : t('pavti.noFollowUp')}</p>
            </div>
          )}
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
            <dt className="text-slate-500">{t('list.createdAt')}</dt>
            <dd>{formatStamp(payment.created_at)}</dd>
            {payment.created_by_name && (
              <>
                <dt className="text-slate-500">{t('list.createdBy')}</dt>
                <dd>{payment.created_by_name}</dd>
              </>
            )}
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

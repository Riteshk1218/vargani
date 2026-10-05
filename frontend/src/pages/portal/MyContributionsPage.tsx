import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Download, FileText, HandHeart, IndianRupee, ReceiptText, UserRoundX } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader, StatCard } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { toApiError } from '../../services/apiClient'
import { saveBlob } from '../../services/finance'
import { openCheckout, portalService } from '../../services/portal'
import type { PortalDue } from '../../types/api'
import { formatDate, formatMoney } from '../../utils/format'
import { PAYMENT_TONE } from '../../utils/payments'

/** The member's own page: what I paid, what is still due, my receipts, and paying online. */
export function MyContributionsPage() {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const [eventId, setEventId] = useState('')
  const [paying, setPaying] = useState<PortalDue | null>(null)
  const params = { event: eventId || undefined }
  const me = useQuery({ queryKey: ['org', activeOrgId, 'portal', 'me'], queryFn: portalService.me, retry: false })
  const ready = me.isSuccess
  const summary = useQuery({ queryKey: ['org', activeOrgId, 'portal', 'summary', eventId], queryFn: () => portalService.summary(params), enabled: ready })
  const payments = useQuery({ queryKey: ['org', activeOrgId, 'portal', 'payments', eventId], queryFn: () => portalService.payments(params), enabled: ready })
  const receipts = useQuery({ queryKey: ['org', activeOrgId, 'portal', 'receipts', eventId], queryFn: () => portalService.receipts(params), enabled: ready })

  if (me.isLoading) return <SkeletonRows rows={6} />
  if (me.isError) {
    const error = toApiError(me.error)
    const known = error.code === 'portal_not_linked' || error.code === 'portal_unavailable'
    return (
      <Card>
        {known ? (
          <EmptyState icon={<UserRoundX className="size-6" />} title={t(`portal.${error.code}`)} message={error.message} />
        ) : (
          <ErrorState message={error.message} onRetry={() => void me.refetch()} />
        )}
      </Card>
    )
  }
  const profile = me.data!
  const currency = profile.organization.currency
  const s = summary.data

  return (
    <div className="space-y-6">
      <PageHeader title={t('portal.title')} description={`${profile.person.full_name} · ${profile.organization.name}`} />
      {profile.events.length > 1 && (
        <div className="sm:w-72">
          <SelectInput label={t('reports.event')} value={eventId} onChange={(e) => setEventId(e.target.value)}>
            <option value="">{t('portal.allEvents')}</option>
            {profile.events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </SelectInput>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label={t('portal.totalPaid')} value={s ? formatMoney(s.total_paid, currency) : '…'} hint={s ? t('portal.paymentsCount', { count: s.payments }) : undefined} icon={<HandHeart className="size-5" />} />
        <StatCard label={t('portal.totalDue')} value={s ? formatMoney(s.total_due, currency) : '…'} icon={<IndianRupee className="size-5" />} />
        <StatCard label={t('portal.receipts')} value={receipts.data?.length ?? '…'} icon={<ReceiptText className="size-5" />} />
      </div>

      <Card>
        <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('portal.dues')}</h2>
        {summary.isLoading ? (
          <SkeletonRows rows={2} />
        ) : summary.isError ? (
          <ErrorState onRetry={() => void summary.refetch()} />
        ) : s!.dues.length === 0 ? (
          <EmptyState title={t('portal.noDues')} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {s!.dues.map((due) => (
              <li key={due.contribution_type} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
                <div className="min-w-0">
                  <p className="font-medium">{due.name}</p>
                  <p className="text-slate-500">
                    {due.event} · {t('portal.paidOf', { paid: formatMoney(due.paid, currency), expected: formatMoney(due.expected, currency) })}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {Number(due.due) > 0 ? (
                    <span className="font-semibold tabular-nums text-red-700">{formatMoney(due.due, currency)}</span>
                  ) : (
                    <Badge tone="green">{t('portal.fullyPaid')}</Badge>
                  )}
                  {profile.online_payments && Number(due.due) > 0 && (
                    <Button size="sm" icon={<CreditCard className="size-4" />} onClick={() => setPaying(due)}>
                      {t('portal.payOnline')}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {!profile.online_payments && (s?.dues.some((d) => Number(d.due) > 0) ?? false) && (
          <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">{t('portal.payCollector')}</p>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('portal.myPayments')}</h2>
          {payments.isLoading ? (
            <SkeletonRows rows={3} />
          ) : payments.isError ? (
            <ErrorState onRetry={() => void payments.refetch()} />
          ) : payments.data!.length === 0 ? (
            <EmptyState title={t('portal.noPayments')} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {payments.data!.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{p.lines.map((l) => l.contribution_type_name).join(', ')}</p>
                    <p className="truncate text-slate-500">
                      {formatDate(p.paid_at)} · {t(`mode.${p.mode}`)} · {p.event_name}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="font-semibold tabular-nums">{formatMoney(p.amount, currency)}</p>
                    {p.status !== 'successful' && <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatus.${p.status}`)}</Badge>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('portal.receipts')}</h2>
          {receipts.isLoading ? (
            <SkeletonRows rows={3} />
          ) : receipts.isError ? (
            <ErrorState onRetry={() => void receipts.refetch()} />
          ) : receipts.data!.length === 0 ? (
            <EmptyState title={t('portal.noReceipts')} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {receipts.data!.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="font-mono font-medium">{r.receipt_number}</p>
                    <p className="text-slate-500">
                      {formatDate(r.issued_at)} · {formatMoney(r.amount, currency)}
                      {r.status === 'void' && ` · ${t('receipts.status.void')}`}
                    </p>
                  </div>
                  <ReceiptButtons id={r.id} number={r.receipt_number} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      {paying && <PayModal due={paying} currency={currency} onClose={() => setPaying(null)} />}
    </div>
  )
}

function ReceiptButtons({ id, number }: { id: string; number: string }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const [busy, setBusy] = useState<'view' | 'save' | null>(null)
  const run = async (how: 'view' | 'save') => {
    setBusy(how)
    // Open the tab first so the browser does not block it as a pop-up.
    const tab = how === 'view' ? window.open('', '_blank') : null
    try {
      const blob = await portalService.receiptPdf(id)
      if (tab) tab.location.href = URL.createObjectURL(blob)
      else saveBlob(blob, `receipt-${number}.pdf`)
    } catch (error) {
      tab?.close()
      notify(toApiError(error).message || t('errors.generic'), 'error')
    } finally {
      setBusy(null)
    }
  }
  return (
    <div className="flex shrink-0 gap-1">
      <Button size="sm" variant="ghost" icon={<FileText className="size-4" />} loading={busy === 'view'} onClick={() => void run('view')}>
        {t('portal.view')}
      </Button>
      <Button size="sm" variant="ghost" icon={<Download className="size-4" />} loading={busy === 'save'} onClick={() => void run('save')} aria-label={t('portal.download')} />
    </div>
  )
}

function PayModal({ due, currency, onClose }: { due: PortalDue; currency: string; onClose: () => void }) {
  const { t, i18n } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [amount, setAmount] = useState(due.due)
  const [error, setError] = useState<string>()
  const eventId = due.event_id
  const pay = useMutation({
    mutationFn: async () => {
      const { checkout } = await portalService.startPayment(eventId!, [{ contribution_type: due.contribution_type, amount }])
      const result = await openCheckout(checkout, i18n.language === 'en' ? 'en' : 'hi')
      if (!result) return 'closed' as const
      await portalService.verifyPayment({ order_id: result.razorpay_order_id, payment_id: result.razorpay_payment_id, signature: result.razorpay_signature })
      return 'paid' as const
    },
    onSuccess: async (outcome) => {
      if (outcome === 'closed') return
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'portal'] })
      notify(t('portal.paid'))
      onClose()
    },
    onError: (err) => {
      const apiError = toApiError(err)
      setError(apiError.details.amount?.[0] ?? apiError.details['lines.0.amount']?.[0] ?? (err instanceof Error && err.message === 'payment_failed' ? t('portal.payFailed') : apiError.message || t('portal.payFailed')))
    },
  })
  return (
    <Modal
      open
      title={t('portal.payOnline')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button icon={<CreditCard className="size-4" />} loading={pay.isPending} disabled={!eventId || !(Number(amount) > 0)} onClick={() => (setError(undefined), pay.mutate())}>
            {t('portal.payAmount', { amount: formatMoney(amount || '0', currency) })}
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-sm">
        <p>
          <span className="font-medium">{due.name}</span> · {due.event}
        </p>
        <TextInput label={t('common.amount')} inputMode="decimal" value={amount} error={error} onChange={(e) => setAmount(e.target.value)} />
        <p className="text-xs text-slate-500">{t('portal.payNote')}</p>
      </div>
    </Modal>
  )
}

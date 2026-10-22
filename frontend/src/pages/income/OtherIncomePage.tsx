import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, PiggyBank, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
import { otherIncomeService } from '../../services/accounts'
import { toApiError } from '../../services/apiClient'
import { fundService } from '../../services/finance'
import type { IncomeSource, OtherIncome, OtherIncomeInput, PaymentMode } from '../../types/api'
import { formatDate, formatMoney, todayIso } from '../../utils/format'
import { INCOME_SOURCES, MANUAL_MODES } from '../../utils/payments'
import { DownloadMenu } from '../../components/DownloadMenu'

/** Income that does not come from a person: donation box (hundi), sponsorship, bank interest, sales. */
export function OtherIncomePage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const isAdmin = can('records.admin_edit')
  const [source, setSource] = useState('')
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState<OtherIncome | true | false>(false)
  const remove = useMutation({
    mutationFn: (id: string) => otherIncomeService.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] }),
    onError,
  })
  const [voiding, setVoiding] = useState<OtherIncome | null>(null)
  const eventId = activeEvent?.id
  const currency = detail?.organization.currency
  const income = useQuery({
    queryKey: ['org', activeOrgId, 'other-income', eventId, source, page],
    queryFn: () => otherIncomeService.list({ event: eventId, source: source || undefined, page }),
    enabled: Boolean(eventId),
  })

  return (
    <div>
      <PageHeader
        title={t('income.title')}
        description={activeEvent ? `${activeEvent.name} · ${t('income.subtitle')}` : t('income.subtitle')}
        actions={
          <>
            <DownloadMenu path="/other-income/" params={{ event: eventId, source }} />
            {eventId && (
              <Button icon={<Plus className="size-4" />} onClick={() => setAdding(true)}>
                {t('income.add')}
              </Button>
            )}
          </>
        }
      />
      <Card>
        {!eventId ? (
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        ) : (
          <>
            <div className="border-b border-slate-200 p-4 sm:w-64">
              <SelectInput label={t('income.source')} value={source} onChange={(e) => (setSource(e.target.value), setPage(1))}>
                <option value="">{t('common.all')}</option>
                {INCOME_SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {t(`incomeSource.${s}`)}
                  </option>
                ))}
              </SelectInput>
            </div>
            {income.isLoading ? (
              <SkeletonRows />
            ) : income.isError ? (
              <ErrorState onRetry={() => void income.refetch()} />
            ) : income.data!.count === 0 ? (
              <EmptyState icon={<PiggyBank className="size-6" />} title={t('income.empty')} message={t('income.emptyMessage')} />
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {income.data!.results.map((i) => (
                    <li key={i.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                      <div className="min-w-0">
                        <p className="truncate font-medium">
                          {t(`incomeSource.${i.source}`)}
                          {i.description && <span className="font-normal text-slate-600"> · {i.description}</span>}
                        </p>
                        <p className="truncate text-slate-500">
                          {formatDate(i.received_on)} · {t(`mode.${i.mode}`)}
                          {i.fund_name && ` · ${i.fund_name}`}
                          {i.status === 'void' && ` · ${t('expenses.voidBecause', { reason: i.void_reason })}`}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <div className="text-right">
                          <p className={i.status === 'void' ? 'font-semibold tabular-nums text-slate-400 line-through' : 'font-semibold tabular-nums'}>
                            {formatMoney(i.amount, currency)}
                          </p>
                          {i.status === 'void' && <Badge>{t('expenseStatus.void')}</Badge>}
                        </div>
                        {i.status === 'recorded' && (
                          <Button size="sm" variant="ghost" onClick={() => setVoiding(i)}>
                            {t('expenses.actions.void')}
                          </Button>
                        )}
                        {isAdmin && (
                          <>
                            <Button size="sm" variant="ghost" aria-label={t('common.edit')} icon={<Pencil className="size-4" />} onClick={() => setAdding(i)} />
                            <Button
                              size="sm"
                              variant="ghost"
                              aria-label={t('common.delete')}
                              icon={<Trash2 className="size-4" />}
                              onClick={() => window.confirm(t('income.deleteConfirm')) && remove.mutate(i.id)}
                            />
                          </>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
                <Pagination page={page} pageSize={25} count={income.data!.count} onChange={setPage} />
              </>
            )}
          </>
        )}
      </Card>
      {adding && eventId && <IncomeFormModal eventId={eventId} income={adding === true ? null : adding} onClose={() => setAdding(false)} />}
      <VoidIncomeModal income={voiding} onClose={() => setVoiding(null)} />
    </div>
  )
}

/** Add income, or (Organization Admin) change any field of existing income. */
function IncomeFormModal({ eventId, income, onClose }: { eventId: string; income: OtherIncome | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const funds = useQuery({ queryKey: ['org', activeOrgId, 'funds', eventId], queryFn: () => fundService.list(eventId) })
  const [form, setForm] = useState<OtherIncomeInput>({
    event: eventId,
    fund: income?.fund ?? null,
    source: income?.source ?? 'donation_box',
    amount: income?.amount ?? '',
    received_on: income?.received_on ?? todayIso(),
    mode: income?.mode ?? 'cash',
    reference_number: income?.reference_number ?? '',
    description: income?.description ?? '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const set = (key: keyof OtherIncomeInput) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const save = useMutation({
    mutationFn: () => (income ? otherIncomeService.update(income.id, form) : otherIncomeService.create(form)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('common.saved'))
      onClose()
    },
    onError: (error) => {
      const apiError = toApiError(error)
      const fieldErrors = Object.fromEntries(Object.entries(apiError.details).map(([k, v]) => [k, v[0]]))
      setErrors(fieldErrors)
      if (Object.keys(fieldErrors).length === 0) notify(apiError.message || t('errors.generic'), 'error')
    },
  })
  return (
    <Modal
      open
      title={income ? t('income.edit') : t('income.add')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => (e.preventDefault(), save.mutate())}>
        <SelectInput label={t('income.source')} required value={form.source} onChange={(e) => setForm((f) => ({ ...f, source: e.target.value as IncomeSource }))}>
          {INCOME_SOURCES.map((s) => (
            <option key={s} value={s}>
              {t(`incomeSource.${s}`)}
            </option>
          ))}
        </SelectInput>
        <TextInput label={t('common.amount')} required inputMode="decimal" value={form.amount} error={errors.amount} onChange={set('amount')} />
        <TextInput label={t('income.receivedOn')} type="date" required max={todayIso()} value={form.received_on} error={errors.received_on} onChange={set('received_on')} />
        <SelectInput label={t('collect.mode')} value={form.mode} onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value as PaymentMode }))}>
          {MANUAL_MODES.map((m) => (
            <option key={m} value={m}>
              {t(`mode.${m}`)}
            </option>
          ))}
        </SelectInput>
        <SelectInput label={t('ctypes.fund')} hint={t('common.optional')} value={form.fund ?? ''} error={errors.fund} onChange={(e) => setForm((f) => ({ ...f, fund: e.target.value || null }))}>
          <option value="">{t('ctypes.noFund')}</option>
          {funds.data?.results.map((fund) => (
            <option key={fund.id} value={fund.id}>
              {fund.name}
            </option>
          ))}
        </SelectInput>
        <TextInput label={t('collect.reference')} hint={t('common.optional')} value={form.reference_number} maxLength={100} onChange={set('reference_number')} />
        <TextInput className="sm:col-span-2" label={t('common.description')} hint={t('common.optional')} value={form.description} maxLength={300} onChange={set('description')} />
      </form>
    </Modal>
  )
}

function VoidIncomeModal({ income, onClose }: { income: OtherIncome | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const [reason, setReason] = useState('')
  const voidIt = useMutation({
    mutationFn: () => otherIncomeService.void(income!.id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      setReason('')
      onClose()
    },
    onError,
  })
  return (
    <Modal
      open={income !== null}
      title={t('income.voidTitle')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="danger" loading={voidIt.isPending} disabled={!reason.trim()} onClick={() => voidIt.mutate()}>
            {t('expenses.actions.void')}
          </Button>
        </>
      }
    >
      {income && (
        <div className="space-y-3 text-sm">
          <p>{t('income.voidMessage', { amount: formatMoney(income.amount, detail?.organization.currency), source: t(`incomeSource.${income.source}`) })}</p>
          <TextInput label={t('payments.reason')} required value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
        </div>
      )}
    </Modal>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Download, FileText, Paperclip, Pencil, Plus, Receipt, Send, Tags, Trash2, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextArea, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { expenseCategoryService, expenseService, type ExpenseAction } from '../../services/accounts'
import { saveBlob } from '../../services/finance'
import { toApiError } from '../../services/apiClient'
import type { Expense, ExpenseInput, PaymentMode } from '../../types/api'
import { formatBytes, formatDate, formatDateTime, formatMoney, todayIso } from '../../utils/format'
import { EXPENSE_STATUSES, EXPENSE_TONE, MANUAL_MODES } from '../../utils/payments'

export function ExpensesPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Expense | 'new' | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [managingCategories, setManagingCategories] = useState(false)
  const eventId = activeEvent?.id
  const currency = detail?.organization.currency
  const categories = useQuery({ queryKey: ['org', activeOrgId, 'expense-categories'], queryFn: expenseCategoryService.list })
  const expenses = useQuery({
    queryKey: ['org', activeOrgId, 'expenses', eventId, status, category, page],
    queryFn: () => expenseService.list({ event: eventId, status: status || undefined, category: category || undefined, page }),
    enabled: Boolean(eventId),
  })

  return (
    <div>
      <PageHeader
        title={t('expenses.title')}
        description={activeEvent ? `${activeEvent.name} · ${t('expenses.subtitle')}` : t('expenses.subtitle')}
        actions={
          <>
            {can('expenses.approve') && (
              <Button variant="secondary" icon={<Tags className="size-4" />} onClick={() => setManagingCategories(true)}>
                {t('expenses.categories')}
              </Button>
            )}
            {can('expenses.create') && eventId && (
              <Button icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
                {t('expenses.add')}
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
            <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:w-2/3">
              <SelectInput label={t('common.status')} value={status} onChange={(e) => (setStatus(e.target.value), setPage(1))}>
                <option value="">{t('common.all')}</option>
                {EXPENSE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {t(`expenseStatus.${s}`)}
                  </option>
                ))}
              </SelectInput>
              <SelectInput label={t('expenses.category')} value={category} onChange={(e) => (setCategory(e.target.value), setPage(1))}>
                <option value="">{t('common.all')}</option>
                {categories.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </SelectInput>
            </div>
            {expenses.isLoading ? (
              <SkeletonRows />
            ) : expenses.isError ? (
              <ErrorState onRetry={() => void expenses.refetch()} />
            ) : expenses.data!.count === 0 ? (
              <EmptyState
                icon={<Receipt className="size-6" />}
                title={status || category ? t('people.noMatches') : t('expenses.empty')}
                message={status || category ? undefined : t('expenses.emptyMessage')}
              />
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {expenses.data!.results.map((e) => (
                    <li key={e.id}>
                      <button type="button" onClick={() => setSelectedId(e.id)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50">
                        <div className="min-w-0">
                          <p className="truncate font-medium">
                            {e.payee}
                            {e.attachments.length > 0 && <Paperclip className="ml-1 inline size-3.5 text-slate-400" aria-label={t('expenses.hasBills')} />}
                          </p>
                          <p className="truncate text-slate-500">
                            {formatDate(e.expense_date)} · {e.category_name} · {t(`mode.${e.mode}`)}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className={e.status === 'void' ? 'font-semibold tabular-nums text-slate-400 line-through' : 'font-semibold tabular-nums'}>
                            {formatMoney(e.amount, currency)}
                          </p>
                          <Badge tone={EXPENSE_TONE[e.status]}>{t(`expenseStatus.${e.status}`)}</Badge>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
                <Pagination page={page} pageSize={25} count={expenses.data!.count} onChange={setPage} />
              </>
            )}
          </>
        )}
      </Card>
      {editing && eventId && (
        <ExpenseFormModal
          expense={editing === 'new' ? null : editing}
          eventId={eventId}
          onClose={() => setEditing(null)}
          onSaved={(e) => (setEditing(null), setSelectedId(e.id))}
        />
      )}
      {selectedId && <ExpenseDetailModal id={selectedId} onClose={() => setSelectedId(null)} onEdit={(e) => (setSelectedId(null), setEditing(e))} />}
      <CategoriesModal open={managingCategories} onClose={() => setManagingCategories(false)} />
    </div>
  )
}

function ExpenseFormModal({ expense, eventId, onClose, onSaved }: { expense: Expense | null; eventId: string; onClose: () => void; onSaved: (e: Expense) => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const categories = useQuery({ queryKey: ['org', activeOrgId, 'expense-categories'], queryFn: expenseCategoryService.list })
  const [form, setForm] = useState<ExpenseInput>(() => ({
    event: eventId,
    category: expense?.category ?? '',
    amount: expense?.amount ?? '',
    expense_date: expense?.expense_date ?? todayIso(),
    mode: expense?.mode ?? 'cash',
    payee: expense?.payee ?? '',
    description: expense?.description ?? '',
    reference_number: expense?.reference_number ?? '',
  }))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const set = (key: keyof ExpenseInput) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const save = useMutation({
    mutationFn: () => (expense ? expenseService.update(expense.id, form) : expenseService.create(form)),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('common.saved'))
      onSaved(saved)
    },
    onError: (error) => {
      const apiError = toApiError(error)
      const fieldErrors = Object.fromEntries(Object.entries(apiError.details).map(([k, v]) => [k, v[0]]))
      setErrors(fieldErrors)
      if (Object.keys(fieldErrors).length === 0) notify(apiError.message || t('errors.generic'), 'error')
    },
  })
  const active = categories.data?.filter((c) => c.is_active || c.id === form.category) ?? []

  return (
    <Modal
      open
      title={expense ? t('expenses.edit') : t('expenses.add')}
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
        <SelectInput label={t('expenses.category')} required value={form.category} error={errors.category} onChange={set('category')}>
          <option value="">{t('common.choose')}</option>
          {active.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </SelectInput>
        <TextInput label={t('common.amount')} required inputMode="decimal" value={form.amount} error={errors.amount} onChange={set('amount')} />
        <TextInput className="sm:col-span-2" label={t('expenses.payee')} required value={form.payee} maxLength={200} error={errors.payee} onChange={set('payee')} />
        <TextInput label={t('expenses.date')} type="date" required max={todayIso()} value={form.expense_date} error={errors.expense_date} onChange={set('expense_date')} />
        <SelectInput label={t('collect.mode')} value={form.mode} error={errors.mode} onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value as PaymentMode }))}>
          {MANUAL_MODES.map((m) => (
            <option key={m} value={m}>
              {t(`mode.${m}`)}
            </option>
          ))}
        </SelectInput>
        <TextInput className="sm:col-span-2" label={t('collect.reference')} hint={t('common.optional')} value={form.reference_number} maxLength={100} onChange={set('reference_number')} />
        <TextArea className="sm:col-span-2" label={t('common.description')} hint={t('common.optional')} rows={3} value={form.description} onChange={set('description')} />
      </form>
    </Modal>
  )
}

function ExpenseDetailModal({ id, onClose, onEdit }: { id: string; onClose: () => void; onEdit: (e: Expense) => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const fileInput = useRef<HTMLInputElement>(null)
  const [action, setAction] = useState<ExpenseAction | null>(null)
  const [reason, setReason] = useState('')
  const expense = useQuery({ queryKey: ['org', activeOrgId, 'expenses', 'detail', id], queryFn: () => expenseService.get(id) })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
  const act = useMutation({
    mutationFn: (a: ExpenseAction) => expenseService.act(id, a, reason),
    onSuccess: async () => {
      await refresh()
      notify(t('common.saved'))
      setAction(null)
      setReason('')
    },
    onError,
  })
  const upload = useMutation({
    mutationFn: (file: File) => expenseService.upload(id, file),
    onSuccess: async () => (await refresh(), notify(t('expenses.billAdded'))),
    onError,
  })
  const remove = useMutation({ mutationFn: (attachmentId: string) => expenseService.removeAttachment(id, attachmentId), onSuccess: refresh, onError })
  const download = useMutation({
    mutationFn: async ({ attachmentId, name }: { attachmentId: string; name: string }) => saveBlob(await expenseService.download(id, attachmentId), name),
    onError,
  })
  const e = expense.data
  const currency = detail?.organization.currency
  const changeable = e && ['draft', 'submitted', 'rejected'].includes(e.status)
  const canCreate = can('expenses.create')
  const canApprove = can('expenses.approve')
  const needsReason = action === 'reject' || action === 'void'

  const footer = !e ? null : action ? (
    <>
      <Button variant="secondary" onClick={() => setAction(null)}>
        {t('common.back')}
      </Button>
      <Button variant={action === 'approve' || action === 'submit' ? 'primary' : 'danger'} loading={act.isPending} disabled={needsReason && !reason.trim()} onClick={() => act.mutate(action)}>
        {t(`expenses.actions.${action}`)}
      </Button>
    </>
  ) : (
    <>
      {canCreate && e.status !== 'void' && (e.status !== 'approved' || canApprove) && (
        <Button variant="ghost" icon={<X className="size-4" />} onClick={() => setAction('void')}>
          {t('expenses.actions.void')}
        </Button>
      )}
      {canCreate && changeable && (
        <Button variant="secondary" icon={<Pencil className="size-4" />} onClick={() => onEdit(e)}>
          {t('common.edit')}
        </Button>
      )}
      {canApprove && e.status === 'submitted' && (
        <>
          <Button variant="secondary" onClick={() => setAction('reject')}>
            {t('expenses.actions.reject')}
          </Button>
          <Button icon={<Check className="size-4" />} onClick={() => setAction('approve')}>
            {t('expenses.actions.approve')}
          </Button>
        </>
      )}
      {canCreate && (e.status === 'draft' || e.status === 'rejected') && (
        <Button icon={<Send className="size-4" />} onClick={() => setAction('submit')}>
          {t('expenses.actions.submit')}
        </Button>
      )}
    </>
  )

  return (
    <Modal open title={e ? e.payee : t('expenses.title')} onClose={onClose} footer={footer} size="lg">
      {!e ? (
        expense.isError ? <ErrorState onRetry={() => void expense.refetch()} /> : <SkeletonRows rows={3} />
      ) : action ? (
        <div className="space-y-3 text-sm">
          <p>{t(`expenses.confirm.${action}`, { amount: formatMoney(e.amount, currency), payee: e.payee })}</p>
          {needsReason && <TextInput label={t('payments.reason')} required value={reason} maxLength={300} onChange={(ev) => setReason(ev.target.value)} />}
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className={e.status === 'void' ? 'text-2xl font-semibold tabular-nums text-slate-400 line-through' : 'text-2xl font-semibold tabular-nums'}>
              {formatMoney(e.amount, currency)}
            </span>
            <Badge tone={EXPENSE_TONE[e.status]}>{t(`expenseStatus.${e.status}`)}</Badge>
          </div>
          {e.status === 'rejected' && e.rejection_reason && <p className="rounded-lg bg-red-50 p-3 text-red-800">{t('expenses.rejectedBecause', { reason: e.rejection_reason })}</p>}
          {e.status === 'void' && <p className="rounded-lg bg-slate-100 p-3 text-slate-700">{t('expenses.voidBecause', { reason: e.void_reason })}</p>}
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1">
            <dt className="text-slate-500">{t('expenses.category')}</dt>
            <dd>{e.category_name}</dd>
            <dt className="text-slate-500">{t('expenses.date')}</dt>
            <dd>{formatDate(e.expense_date)}</dd>
            <dt className="text-slate-500">{t('collect.mode')}</dt>
            <dd>
              {t(`mode.${e.mode}`)}
              {e.reference_number && ` · ${e.reference_number}`}
            </dd>
            {e.description && (
              <>
                <dt className="text-slate-500">{t('common.description')}</dt>
                <dd className="whitespace-pre-line">{e.description}</dd>
              </>
            )}
            <dt className="text-slate-500">{t('expenses.createdBy')}</dt>
            <dd>
              {e.created_by_name ?? '—'} · {formatDateTime(e.created_at)}
            </dd>
            {e.submitted_by_name && (
              <>
                <dt className="text-slate-500">{t('expenses.submittedBy')}</dt>
                <dd>
                  {e.submitted_by_name} · {formatDateTime(e.submitted_at)}
                </dd>
              </>
            )}
            {e.decided_by_name && (
              <>
                <dt className="text-slate-500">{e.status === 'rejected' ? t('expenses.rejectedBy') : t('expenses.approvedBy')}</dt>
                <dd>
                  {e.decided_by_name} · {formatDateTime(e.decided_at)}
                </dd>
              </>
            )}
          </dl>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold">{t('expenses.bills')}</h3>
              {canCreate && changeable && e.attachments.length < 10 && (
                <>
                  <input
                    ref={fileInput}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    className="hidden"
                    onChange={(ev) => {
                      const file = ev.target.files?.[0]
                      if (file) upload.mutate(file)
                      ev.target.value = ''
                    }}
                  />
                  <Button size="sm" variant="secondary" loading={upload.isPending} icon={<Paperclip className="size-4" />} onClick={() => fileInput.current?.click()}>
                    {t('expenses.addBill')}
                  </Button>
                </>
              )}
            </div>
            {e.attachments.length === 0 ? (
              <p className="text-slate-500">{t('expenses.noBills')}</p>
            ) : (
              <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
                {e.attachments.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="flex min-w-0 items-center gap-2">
                      <FileText className="size-4 shrink-0 text-slate-400" aria-hidden />
                      <span className="truncate">{a.original_name}</span>
                      <span className="shrink-0 text-xs text-slate-500">{formatBytes(a.size_bytes)}</span>
                    </span>
                    <span className="flex shrink-0 gap-1">
                      <Button size="sm" variant="ghost" aria-label={t('common.download')} icon={<Download className="size-4" />} onClick={() => download.mutate({ attachmentId: a.id, name: a.original_name })} />
                      {canCreate && changeable && (
                        <Button size="sm" variant="ghost" aria-label={t('common.remove')} icon={<Trash2 className="size-4" />} onClick={() => remove.mutate(a.id)} />
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-1 text-xs text-slate-500">{t('expenses.billHelp')}</p>
          </div>
        </div>
      )}
    </Modal>
  )
}

function CategoriesModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const [name, setName] = useState('')
  const categories = useQuery({ queryKey: ['org', activeOrgId, 'expense-categories'], queryFn: expenseCategoryService.list, enabled: open })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'expense-categories'] })
  const add = useMutation({ mutationFn: () => expenseCategoryService.create(name), onSuccess: async () => (await refresh(), setName('')), onError })
  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => expenseCategoryService.update(id, { is_active }),
    onSuccess: refresh,
    onError,
  })
  return (
    <Modal open={open} title={t('expenses.categories')} onClose={onClose}>
      <form className="mb-4 flex items-end gap-2" onSubmit={(e) => (e.preventDefault(), name.trim() && add.mutate())}>
        <TextInput className="flex-1" label={t('expenses.newCategory')} value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={add.isPending} disabled={!name.trim()} icon={<Plus className="size-4" />}>
          {t('common.add')}
        </Button>
      </form>
      <ul className="divide-y divide-slate-100 text-sm">
        {categories.data?.map((c) => (
          <li key={c.id} className="flex items-center justify-between py-2">
            <span className={c.is_active ? '' : 'text-slate-400 line-through'}>{c.name}</span>
            <Button size="sm" variant="ghost" onClick={() => toggle.mutate({ id: c.id, is_active: !c.is_active })}>
              {c.is_active ? t('common.archive') : t('common.restore')}
            </Button>
          </li>
        ))}
      </ul>
    </Modal>
  )
}

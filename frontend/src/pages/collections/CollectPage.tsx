import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Plus, ReceiptText, Search, Trash2, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card, PageHeader } from '../../components/ui/Card'
import { Checkbox, SelectInput, TextInput } from '../../components/ui/Field'
import { EmptyState, Spinner } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useDebounced } from '../../hooks/useDebounced'
import { toApiError } from '../../services/apiClient'
import { contributionTypeService, paymentService } from '../../services/finance'
import { peopleService } from '../../services/people'
import type { ContributionType, Payment, PaymentInput, PaymentMode, Person } from '../../types/api'
import { formatMobile, formatMoney, sumMoney } from '../../utils/format'
import { MANUAL_MODES } from '../../utils/payments'

const MONEY = /^\d+(\.\d{1,2})?$/

interface Line {
  key: number
  typeId: string
  month: string // YYYY-MM
  amount: string
}

function today() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

function newKey() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
}

export function CollectPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const { activeEvent, events, setActiveEventId } = useEvents()
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const currency = detail?.organization.currency

  // ?event= and ?person= let other pages open this form pre-filled.
  useEffect(() => {
    const wanted = params.get('event')
    if (wanted && events.some((e) => e.id === wanted) && activeEvent?.id !== wanted) setActiveEventId(wanted)
  }, [params, events, activeEvent, setActiveEventId])

  const [person, setPerson] = useState<Person | null>(null)
  const replaces = params.get('replaces')
  const presetPerson = params.get('person')
  const preset = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'detail', presetPerson],
    queryFn: () => peopleService.get(presetPerson!),
    enabled: Boolean(presetPerson) && !person,
  })
  useEffect(() => {
    if (preset.data && !person) setPerson(preset.data)
  }, [preset.data, person])

  const eventId = activeEvent?.id ?? ''
  const types = useQuery({
    queryKey: ['org', activeOrgId, 'contribution-types', eventId, 'active'],
    queryFn: () => contributionTypeService.list(eventId, { is_active: true }),
    enabled: Boolean(eventId),
  })
  const activeTypes = useMemo(() => types.data?.results ?? [], [types.data])

  const [lines, setLines] = useState<Line[]>([])
  const [mode, setMode] = useState<PaymentMode>('cash')
  const [reference, setReference] = useState('')
  const [chequeBank, setChequeBank] = useState('')
  const [chequeDate, setChequeDate] = useState('')
  const [pending, setPending] = useState(false)
  const [paidOn, setPaidOn] = useState(today())
  const [notes, setNotes] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState<Payment | null>(null)
  const [idempotencyKey, setIdempotencyKey] = useState(newKey)

  // New lines start on the monthly type, the most common collection.
  const defaultType = activeTypes.find((ct) => ct.kind === 'recurring_monthly') ?? activeTypes[0]
  const blankLine = (key: number): Line => ({ key, typeId: defaultType?.id ?? '', month: today().slice(0, 7), amount: '' })
  useEffect(() => {
    if (activeTypes.length) setLines((current) => (current.length ? current : [blankLine(1)]))
  }, [activeTypes])

  const typeById = (id: string): ContributionType | undefined => activeTypes.find((ct) => ct.id === id)
  const total = sumMoney(lines.map((l) => (MONEY.test(l.amount) ? l.amount : '0')))
  const updateLine = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const reset = () => {
    setPerson(null)
    setLines([blankLine(1)])
    setMode('cash')
    setReference('')
    setChequeBank('')
    setChequeDate('')
    setPending(false)
    setPaidOn(today())
    setNotes('')
    setErrors({})
    setDone(null)
    setIdempotencyKey(newKey())
    if (params.get('person') || params.get('replaces')) setParams({})
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const found: Record<string, string> = {}
    if (!person) found.payer = t('collect.choosePerson')
    lines.forEach((line, index) => {
      if (!MONEY.test(line.amount) || sumMoney([line.amount]) === '0.00') found[`lines.${index}.amount`] = t('validation.amount')
      if (typeById(line.typeId)?.kind === 'recurring_monthly' && !line.month) found[`lines.${index}.period_month`] = t('validation.required')
    })
    if ((mode === 'cheque' || mode === 'bank_transfer') && !reference.trim()) found.reference_number = t('validation.required')
    setErrors(found)
    if (Object.keys(found).length || !person) return

    const payload: PaymentInput = {
      event: eventId,
      payer: person.id,
      mode,
      status: mode === 'cheque' && pending ? 'pending' : 'successful',
      amount: total,
      reference_number: reference.trim(),
      cheque_bank: mode === 'cheque' ? chequeBank : '',
      cheque_date: mode === 'cheque' && chequeDate ? chequeDate : null,
      notes,
      lines: lines.map((line) => ({
        contribution_type: line.typeId,
        amount: line.amount,
        period_month: typeById(line.typeId)?.kind === 'recurring_monthly' ? `${line.month}-01` : null,
      })),
    }
    if (replaces) payload.replaces_receipt = replaces
    if (paidOn && paidOn !== today()) payload.paid_at = new Date(`${paidOn}T12:00:00`).toISOString()

    setSubmitting(true)
    try {
      const payment = await paymentService.record(payload, idempotencyKey)
      setDone(payment)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
    } catch (error) {
      const apiError = toApiError(error)
      const fieldErrors: Record<string, string> = {}
      for (const [field, messages] of Object.entries(apiError.details)) if (messages[0]) fieldErrors[field] = messages[0]
      setErrors(fieldErrors)
      notify(apiError.message || t('errors.generic'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  if (!activeEvent) {
    return (
      <div>
        <PageHeader title={t('collect.title')} />
        <Card>
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        </Card>
      </div>
    )
  }

  if (done) {
    return (
      <div className="mx-auto max-w-lg">
        <Card className="p-6 text-center">
          <CheckCircle2 className="mx-auto size-12 text-emerald-600" aria-hidden />
          <h1 className="mt-3 text-lg font-semibold">
            {done.receipt ? t('collect.success', { number: done.receipt.receipt_number }) : t('collect.pendingSaved')}
          </h1>
          <p className="mt-1 text-slate-600">
            {done.payer_name} · {formatMoney(done.amount, currency)} · {t(`mode.${done.mode}`)}
          </p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            {done.receipt && (
              <Link to={`/app/receipts/${done.receipt.id}`}>
                <Button icon={<ReceiptText className="size-4" />} className="w-full">
                  {t('collect.viewReceipt')}
                </Button>
              </Link>
            )}
            <Button variant="secondary" onClick={reset}>
              {t('collect.another')}
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  const eventInactive = activeEvent.status !== 'active'
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title={t('collect.title')} description={`${activeEvent.name} · ${t('collect.subtitle')}`} />
      {eventInactive ? (
        <Card>
          <EmptyState title={t('collect.eventNotActive')} />
        </Card>
      ) : types.isLoading ? (
        <Spinner />
      ) : activeTypes.length === 0 ? (
        <Card>
          <EmptyState
            title={t('collect.noTypes')}
            message={t('collect.noTypesManage')}
            action={
              <Link to={`/app/events/${activeEvent.id}`}>
                <Button variant="secondary">{t('collect.openEvent')}</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {replaces && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">{t('collect.correctionNote')}</p>}
          <Card className="p-4">
            <PersonPicker person={person} onChange={setPerson} error={errors.payer} />
          </Card>

          <Card className="space-y-4 p-4">
            {lines.map((line, index) => {
              const ct = typeById(line.typeId)
              const range = [ct?.suggested_min, ct?.suggested_max].filter(Boolean).map((v) => formatMoney(v, currency)).join(' – ')
              return (
                <div key={line.key} className="grid gap-3 border-b border-slate-100 pb-4 last:border-0 last:pb-0 sm:grid-cols-[1fr_9rem_8rem_auto] sm:items-start">
                  <SelectInput
                    label={t('collect.type')}
                    value={line.typeId}
                    error={errors[`lines.${index}.contribution_type`]}
                    onChange={(e) => updateLine(line.key, { typeId: e.target.value })}
                  >
                    {activeTypes.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </SelectInput>
                  {ct?.kind === 'recurring_monthly' ? (
                    <TextInput
                      label={t('collect.month')}
                      type="month"
                      value={line.month}
                      error={errors[`lines.${index}.period_month`]}
                      onChange={(e) => updateLine(line.key, { month: e.target.value })}
                    />
                  ) : (
                    <div className="hidden sm:block" />
                  )}
                  <TextInput
                    label={t('common.amount')}
                    inputMode="decimal"
                    value={line.amount}
                    placeholder="0"
                    hint={range ? t('collect.suggested', { range }) : undefined}
                    error={errors[`lines.${index}.amount`]}
                    onChange={(e) => updateLine(line.key, { amount: e.target.value.replace(/[^\d.]/g, '') })}
                  />
                  {lines.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="sm:mt-7"
                      aria-label={t('collect.removeLine')}
                      onClick={() => setLines((ls) => ls.filter((l) => l.key !== line.key))}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  )}
                </div>
              )
            })}
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                size="sm"
                icon={<Plus className="size-4" />}
                onClick={() => setLines((ls) => [...ls, blankLine(Math.max(0, ...ls.map((l) => l.key)) + 1)])}
              >
                {t('collect.addLine')}
              </Button>
              <p className="text-right">
                <span className="text-sm text-slate-500">{t('common.total')} </span>
                <span className="text-xl font-semibold" data-testid="collect-total">
                  {formatMoney(total, currency)}
                </span>
              </p>
            </div>
          </Card>

          <Card className="grid gap-4 p-4 sm:grid-cols-2">
            <SelectInput label={t('collect.mode')} value={mode} onChange={(e) => setMode(e.target.value as PaymentMode)}>
              {MANUAL_MODES.map((m) => (
                <option key={m} value={m}>
                  {t(`mode.${m}`)}
                </option>
              ))}
            </SelectInput>
            <TextInput label={t('collect.paidOn')} type="date" max={today()} value={paidOn} error={errors.paid_at} onChange={(e) => setPaidOn(e.target.value)} />
            {mode !== 'cash' && (
              <TextInput
                label={mode === 'cheque' ? t('collect.chequeNumber') : t('collect.reference')}
                required={mode === 'cheque' || mode === 'bank_transfer'}
                hint={mode === 'upi' || mode === 'other' ? t('common.optional') : undefined}
                value={reference}
                error={errors.reference_number}
                onChange={(e) => setReference(e.target.value)}
              />
            )}
            {mode === 'cheque' && (
              <>
                <TextInput label={t('collect.chequeBank')} value={chequeBank} onChange={(e) => setChequeBank(e.target.value)} />
                <TextInput label={t('collect.chequeDate')} type="date" value={chequeDate} onChange={(e) => setChequeDate(e.target.value)} />
                <Checkbox className="sm:col-span-2" label={t('collect.pending')} checked={pending} onChange={(e) => setPending(e.target.checked)} />
              </>
            )}
            <TextInput className="sm:col-span-2" label={t('common.notes')} hint={t('common.optional')} value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} />
          </Card>

          <Button type="submit" loading={submitting} className="w-full" icon={<ReceiptText className="size-4" />}>
            {mode === 'cheque' && pending ? t('collect.submitPending') : t('collect.submit', { amount: formatMoney(total, currency) })}
          </Button>
        </form>
      )}
    </div>
  )
}

function PersonPicker({ person, onChange, error }: { person: Person | null; onChange: (p: Person | null) => void; error?: string }) {
  const { t } = useTranslation()
  const { activeOrgId, can } = useOrg()
  const [search, setSearch] = useState('')
  const debounced = useDebounced(search)
  const people = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'picker', debounced],
    queryFn: () => peopleService.list({ search: debounced || undefined, page_size: 8 }),
    enabled: !person,
  })

  if (person) {
    return (
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-brand-50 text-brand-800">
            <UserRound className="size-5" aria-hidden />
          </span>
          <div>
            <p className="text-xs text-slate-500">{t('collect.person')}</p>
            <p className="font-semibold">{person.full_name}</p>
            <p className="text-sm text-slate-500">{formatMobile(person.mobile)}</p>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => onChange(null)}>
          {t('collect.change')}
        </Button>
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <div className="relative">
        <TextInput label={t('collect.person')} placeholder={t('collect.searchPerson')} value={search} error={error} onChange={(e) => setSearch(e.target.value)} />
        <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
      </div>
      {people.isLoading ? (
        <Spinner />
      ) : (people.data?.results.length ?? 0) === 0 ? (
        <p className="py-3 text-center text-sm text-slate-500">
          {t('people.noMatches')}{' '}
          {can('people.manage') && (
            <Link className="font-medium text-brand-700 underline" to="/app/people?new=1">
              {t('people.add')}
            </Link>
          )}
        </p>
      ) : (
        <ul className="max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-lg ring-1 ring-slate-200">
          {people.data!.results.map((p) => (
            <li key={p.id}>
              <button type="button" className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50" onClick={() => onChange(p)}>
                <span>
                  <span className="font-medium">{p.full_name}</span>
                  <span className="block text-slate-500">{[formatMobile(p.mobile), p.area].filter(Boolean).join(' · ')}</span>
                </span>
                <span className="text-brand-700">{t('collect.select')}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

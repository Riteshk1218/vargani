import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { toApiError } from '../../services/apiClient'
import { contributionTypeService, paymentService } from '../../services/finance'
import { peopleService } from '../../services/people'
import type { NewPersonInput, Payment, PaymentEditInput, PaymentMode, Person } from '../../types/api'
import { formatMoney, sumMoney } from '../../utils/format'
import { MANUAL_MODES } from '../../utils/payments'
import { PayerChoice } from '../collections/CollectPage'

const MONEY = /^\d+(\.\d{1,2})?$/

interface Line {
  key: number
  typeId: string
  month: string
  amount: string
}

/** "2026-10-08T22:35" in the browser's time zone, for a datetime-local input. */
function toLocalInput(iso: string) {
  const date = new Date(iso)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

/** Organization Admin: change anything about a recorded collection. The receipt keeps its number. */
export function PaymentEditModal({ payment, onClose, onSaved }: { payment: Payment; onClose: () => void; onSaved: (p: Payment) => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const currency = detail?.organization.currency

  const types = useQuery({
    queryKey: ['org', activeOrgId, 'contribution-types', payment.event, 'all'],
    queryFn: () => contributionTypeService.list(payment.event),
  })
  const payerQuery = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'detail', payment.payer],
    queryFn: () => peopleService.get(payment.payer!),
    enabled: Boolean(payment.payer),
  })

  const [kind, setKind] = useState<'existing' | 'new' | 'anonymous'>(payment.payer ? 'existing' : 'anonymous')
  const [chosen, setChosen] = useState<Person | null | undefined>(undefined) // undefined: unchanged
  const person = chosen === undefined ? (payerQuery.data ?? null) : chosen
  const [newPerson, setNewPerson] = useState<NewPersonInput>({ full_name: '' })
  const [lines, setLines] = useState<Line[]>(() =>
    payment.lines.map((line, index) => ({
      key: index + 1,
      typeId: line.contribution_type,
      month: line.period_month ? line.period_month.slice(0, 7) : '',
      amount: line.amount,
    })),
  )
  const [mode, setMode] = useState<PaymentMode>(payment.mode)
  const [reference, setReference] = useState(payment.reference_number)
  const [paidAt, setPaidAt] = useState(toLocalInput(payment.paid_at))
  const [notes, setNotes] = useState(payment.notes)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  const typeList = types.data?.results ?? []
  const typeById = (id: string) => typeList.find((ct) => ct.id === id)
  const total = sumMoney(lines.map((l) => (MONEY.test(l.amount) ? l.amount : '0')))
  const update = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const save = async () => {
    const found: Record<string, string> = {}
    lines.forEach((line, index) => {
      if (!MONEY.test(line.amount) || sumMoney([line.amount]) === '0.00') found[`lines.${index}.amount`] = t('validation.amount')
      if (typeById(line.typeId)?.kind === 'recurring_monthly' && !line.month) found[`lines.${index}.period_month`] = t('validation.required')
    })
    if (kind === 'new' && !newPerson.full_name.trim()) found['new_person.full_name'] = t('validation.required')
    setErrors(found)
    if (Object.keys(found).length) return

    const input: PaymentEditInput = {
      mode,
      reference_number: reference.trim(),
      paid_at: new Date(paidAt).toISOString(),
      notes,
      lines: lines.map((line) => ({
        contribution_type: line.typeId,
        amount: line.amount,
        period_month: typeById(line.typeId)?.kind === 'recurring_monthly' ? `${line.month}-01` : null,
      })),
    }
    if (kind === 'new') input.new_person = { ...newPerson, full_name: newPerson.full_name.trim() }
    else input.payer = kind === 'existing' && person ? person.id : null

    setSaving(true)
    try {
      const saved = await paymentService.adminEdit(payment.id, input)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('common.saved'))
      onSaved(saved)
    } catch (error) {
      const apiError = toApiError(error)
      const fieldErrors: Record<string, string> = {}
      for (const [field, messages] of Object.entries(apiError.details)) if (Array.isArray(messages) && messages[0]) fieldErrors[field] = messages[0]
      setErrors(fieldErrors)
      notify(apiError.message || t('errors.generic'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      size="lg"
      title={t('payments.editTitle')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button loading={saving} onClick={() => void save()}>
            {t('payments.saveChanges', { amount: formatMoney(total, currency) })}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <p className="rounded-lg bg-amber-50 p-3 text-amber-900 ring-1 ring-amber-200">{t('payments.editNote')}</p>
        <PayerChoice
          kind={kind}
          onKind={setKind}
          person={person}
          onPerson={setChosen}
          newPerson={newPerson}
          onNewPerson={setNewPerson}
          errors={errors}
        />
        <div className="space-y-3">
          {lines.map((line, index) => (
            <div key={line.key} className="grid gap-2 sm:grid-cols-[1fr_8rem_8rem_auto] sm:items-start">
              <SelectInput label={t('collect.type')} value={line.typeId} error={errors[`lines.${index}.contribution_type`]} onChange={(e) => update(line.key, { typeId: e.target.value })}>
                {typeList.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </SelectInput>
              {typeById(line.typeId)?.kind === 'recurring_monthly' ? (
                <TextInput label={t('collect.month')} type="month" value={line.month} error={errors[`lines.${index}.period_month`]} onChange={(e) => update(line.key, { month: e.target.value })} />
              ) : (
                <div className="hidden sm:block" />
              )}
              <TextInput
                label={t('common.amount')}
                inputMode="decimal"
                value={line.amount}
                error={errors[`lines.${index}.amount`]}
                onChange={(e) => update(line.key, { amount: e.target.value.replace(/[^\d.]/g, '') })}
              />
              {lines.length > 1 && (
                <Button variant="ghost" size="sm" className="sm:mt-7" aria-label={t('collect.removeLine')} onClick={() => setLines((ls) => ls.filter((l) => l.key !== line.key))}>
                  <Trash2 className="size-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            variant="secondary"
            size="sm"
            icon={<Plus className="size-4" />}
            onClick={() => setLines((ls) => [...ls, { key: Math.max(0, ...ls.map((l) => l.key)) + 1, typeId: typeList[0]?.id ?? '', month: '', amount: '' }])}
          >
            {t('collect.addLine')}
          </Button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectInput label={t('collect.mode')} value={mode} onChange={(e) => setMode(e.target.value as PaymentMode)}>
            {MANUAL_MODES.map((m) => (
              <option key={m} value={m}>
                {t(`mode.${m}`)}
              </option>
            ))}
          </SelectInput>
          <TextInput label={t('payments.dateTime')} type="datetime-local" value={paidAt} error={errors.paid_at} onChange={(e) => setPaidAt(e.target.value)} />
          {mode !== 'cash' && (
            <TextInput label={t('collect.reference')} value={reference} error={errors.reference_number} onChange={(e) => setReference(e.target.value)} />
          )}
          <TextInput className="sm:col-span-2" label={t('common.notes')} value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
    </Modal>
  )
}

import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { toApiError } from '../../services/apiClient'
import { paymentService } from '../../services/finance'
import type { Payment, PaymentMode, PavtiVisitInput } from '../../types/api'
import { formatDate, formatMoney } from '../../utils/format'
import { MANUAL_MODES, todayIso } from '../../utils/payments'

const MONEY = /^\d+(\.\d{1,2})?$/

/** A later visit to a house: add the money that came now to the same pavti and set the next follow-up date.
 * No new pavti is made. */
export function PavtiVisitModal({ payment, onClose, onSaved }: { payment: Payment; onClose: () => void; onSaved: (p: Payment) => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const currency = detail?.organization.currency
  const owed = payment.balance_due
  const [received, setReceived] = useState('')
  const [mode, setMode] = useState<PaymentMode>(Number(payment.amount) > 0 ? payment.mode : 'cash')
  const [reference, setReference] = useState('')
  const [followUp, setFollowUp] = useState(payment.follow_up_on && payment.follow_up_on >= todayIso() ? payment.follow_up_on : todayIso(1))
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  const amount = received === '' ? '0' : received
  const paysAll = MONEY.test(amount) && Number(amount) >= Number(owed)
  const left = Math.max(0, Number(owed) - (MONEY.test(amount) ? Number(amount) : 0)).toFixed(2)

  const save = async () => {
    const found: Record<string, string> = {}
    if (!MONEY.test(amount) || Number(amount) > Number(owed)) found.received = t('pavti.tooMuch', { amount: formatMoney(owed, currency) })
    if (Number(amount) > 0 && (mode === 'cheque' || mode === 'bank_transfer') && !reference.trim()) found.reference_number = t('validation.required')
    if (!paysAll && followUp && followUp < todayIso()) found.follow_up_on = t('pavti.datePast')
    setErrors(found)
    if (Object.keys(found).length) return
    const input: PavtiVisitInput = { received: amount, follow_up_on: paysAll ? null : followUp || null }
    if (Number(amount) > 0) {
      input.mode = mode
      input.reference_number = reference.trim()
    }
    setSaving(true)
    try {
      const saved = await paymentService.visit(payment.id, input)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(saved.pavti_status === 'paid' ? t('pavti.nowPaid') : t('common.saved'))
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
      title={t('pavti.updateTitle')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button loading={saving} onClick={() => void save()}>
            {paysAll ? t('pavti.markPaid') : Number(amount) > 0 ? t('pavti.saveReceived', { amount: formatMoney(amount, currency) }) : t('pavti.saveDate')}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <div className="rounded-lg bg-amber-50 p-3 text-amber-900 ring-1 ring-amber-200">
          <p className="font-semibold">{payment.payer_name}</p>
          <p>
            {[payment.receipt?.receipt_number, t('pavti.stillOwed', { amount: formatMoney(owed, currency) })].filter(Boolean).join(' · ')}
          </p>
          {payment.follow_up_on && <p>{t('pavti.lastFollowUp', { date: formatDate(payment.follow_up_on) })}</p>}
        </div>
        <div>
          <TextInput
            label={t('pavti.receivedNow')}
            inputMode="decimal"
            placeholder="0"
            value={received}
            hint={t('pavti.receivedHint')}
            error={errors.received}
            onChange={(e) => setReceived(e.target.value.replace(/[^\d.]/g, ''))}
          />
          <Button size="sm" variant="secondary" className="mt-2" onClick={() => setReceived(owed)}>
            {t('pavti.paidInFull', { amount: formatMoney(owed, currency) })}
          </Button>
        </div>
        {Number(amount) > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            <SelectInput label={t('collect.mode')} value={mode} onChange={(e) => setMode(e.target.value as PaymentMode)}>
              {MANUAL_MODES.map((m) => (
                <option key={m} value={m}>
                  {t(`mode.${m}`)}
                </option>
              ))}
            </SelectInput>
            {mode !== 'cash' && (
              <TextInput
                label={mode === 'cheque' ? t('collect.chequeNumber') : t('collect.reference')}
                hint={mode === 'upi' || mode === 'other' ? t('common.optional') : undefined}
                value={reference}
                error={errors.reference_number}
                onChange={(e) => setReference(e.target.value)}
              />
            )}
          </div>
        )}
        {paysAll ? (
          <p className="rounded-lg bg-emerald-50 p-3 font-medium text-emerald-800">{t('pavti.willBePaid')}</p>
        ) : (
          <TextInput
            label={t('pavti.nextFollowUp')}
            type="date"
            min={todayIso()}
            value={followUp}
            hint={t('pavti.leftAfter', { amount: formatMoney(left, currency) })}
            error={errors.follow_up_on}
            onChange={(e) => setFollowUp(e.target.value)}
          />
        )}
      </div>
    </Modal>
  )
}

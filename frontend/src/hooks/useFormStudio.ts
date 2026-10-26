import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useOrg } from '../context/OrgContext'
import type { FormStudio, PaymentMode, StudioLabelField } from '../types/api'
import { MANUAL_MODES } from '../utils/payments'

/** The standard name of each Collect field the admin studio can rename. */
export const STUDIO_DEFAULT_LABELS: Record<StudioLabelField, string> = {
  payer: 'collect.person',
  contribution_type: 'collect.type',
  month: 'collect.month',
  amount: 'common.amount',
  received: 'collect.receivedNow',
  follow_up_on: 'pavti.followUpDate',
  mode: 'collect.mode',
  paid_on: 'collect.paidOn',
  reference: 'collect.reference',
  cheque_number: 'collect.chequeNumber',
  cheque_bank: 'collect.chequeBank',
  cheque_date: 'collect.chequeDate',
  notes: 'common.notes',
}

export const EMPTY_STUDIO: FormStudio = { labels: {}, modes: {}, custom_fields: [] }

/** How this organization's admins set up the Collect form (admin studio). */
export function useFormStudio() {
  const { t } = useTranslation()
  const { detail } = useOrg()
  const studio = detail?.form_studio ?? EMPTY_STUDIO
  return useMemo(
    () => ({
      label: (field: StudioLabelField) => studio.labels?.[field] || t(STUDIO_DEFAULT_LABELS[field]),
      modes: MANUAL_MODES.filter((m) => !studio.modes?.[m]?.hidden),
      modeLabel: (mode: PaymentMode) => studio.modes?.[mode]?.label || t(`mode.${mode}`),
      customFields: (studio.custom_fields ?? []).filter((f) => f.active && f.key),
    }),
    [studio, t],
  )
}

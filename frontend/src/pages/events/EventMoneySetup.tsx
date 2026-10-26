import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, ArchiveRestore, Pencil, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card } from '../../components/ui/Card'
import { Checkbox, SelectInput, TextArea, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { contributionTypeService, fundService, type ContributionTypeInput } from '../../services/finance'
import type { ContributionKind, ContributionType, Fund } from '../../types/api'
import { formatMoney } from '../../utils/format'

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/

/** Funds and contribution types of one event: what money is collected for. */
export function EventMoneySetup({ eventId }: { eventId: string }) {
  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <ContributionTypesCard eventId={eventId} />
      <FundsCard eventId={eventId} />
    </div>
  )
}

function useEventMoneyKeys(eventId: string) {
  const { activeOrgId } = useOrg()
  return {
    funds: ['org', activeOrgId, 'funds', eventId],
    types: ['org', activeOrgId, 'contribution-types', eventId],
  }
}

function FundsCard({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { can, detail } = useOrg()
  const keys = useEventMoneyKeys(eventId)
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const [editing, setEditing] = useState<Fund | 'new' | null>(null)
  const funds = useQuery({ queryKey: keys.funds, queryFn: () => fundService.list(eventId) })
  const toggle = useMutation({
    mutationFn: (fund: Fund) => fundService.update(fund.id, { is_active: !fund.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.funds }),
    onError,
  })
  const canManage = can('funds.manage')

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="font-semibold">{t('funds.title')}</h2>
          <p className="text-xs text-slate-500">{t('funds.help')}</p>
        </div>
        {canManage && (
          <Button size="sm" icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
            {t('funds.add')}
          </Button>
        )}
      </div>
      {funds.isLoading ? (
        <SkeletonRows rows={2} />
      ) : funds.isError ? (
        <ErrorState onRetry={() => void funds.refetch()} />
      ) : funds.data!.count === 0 ? (
        <EmptyState title={t('funds.empty')} message={t('funds.emptyMessage')} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {funds.data!.results.map((fund) => (
            <li key={fund.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="font-medium">
                  {fund.name} {!fund.is_active && <Badge>{t('funds.archived')}</Badge>}
                </p>
                {fund.target_amount && (
                  <p className="text-slate-500">
                    {t('events.target')}: {formatMoney(fund.target_amount, detail?.organization.currency)}
                  </p>
                )}
              </div>
              {canManage && (
                <div className="flex shrink-0">
                  <Button variant="ghost" size="sm" aria-label={t('common.edit')} onClick={() => setEditing(fund)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={fund.is_active ? t('funds.archive') : t('funds.restore')}
                    onClick={() => toggle.mutate(fund)}
                  >
                    {fund.is_active ? <Archive className="size-4" /> : <ArchiveRestore className="size-4" />}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <FundModal eventId={eventId} fund={editing === 'new' ? null : editing} open={editing !== null} onClose={() => setEditing(null)} />
    </Card>
  )
}

function FundModal({ eventId, fund, open, onClose }: { eventId: string; fund: Fund | null; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const keys = useEventMoneyKeys(eventId)
  const queryClient = useQueryClient()
  const { register, handleSubmit, reset, setError, formState } = useForm<{ name: string; target_amount: string; description: string }>()
  const onError = useApiErrors(setError, ['name', 'target_amount', 'description'])

  useEffect(() => {
    if (open) reset({ name: fund?.name ?? '', target_amount: fund?.target_amount ?? '', description: fund?.description ?? '' })
  }, [open, fund, reset])

  const onSubmit = handleSubmit(async (values) => {
    const payload = { name: values.name, description: values.description, target_amount: values.target_amount || null }
    try {
      if (fund) await fundService.update(fund.id, payload)
      else await fundService.create({ ...payload, event: eventId })
      await queryClient.invalidateQueries({ queryKey: keys.funds })
      await queryClient.invalidateQueries({ queryKey: keys.types })
      notify(t('common.saved'))
      onClose()
    } catch (error) {
      onError(error)
    }
  })

  return (
    <Modal
      open={open}
      title={fund ? t('funds.edit') : t('funds.add')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="fund-form" loading={formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form id="fund-form" onSubmit={onSubmit} className="space-y-4" noValidate>
        <TextInput
          label={t('funds.name')}
          required
          placeholder={t('funds.namePlaceholder')}
          error={formState.errors.name && (formState.errors.name.message || t('validation.required'))}
          {...register('name', { required: true })}
        />
        <TextInput
          label={t('funds.target')}
          hint={t('common.optional')}
          inputMode="decimal"
          error={formState.errors.target_amount && (formState.errors.target_amount.message || t('validation.amount'))}
          {...register('target_amount', { pattern: MONEY_PATTERN })}
        />
        <TextArea label={t('funds.description')} {...register('description')} />
      </form>
    </Modal>
  )
}

export function ContributionTypesCard({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { can, detail } = useOrg()
  const keys = useEventMoneyKeys(eventId)
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const [editing, setEditing] = useState<ContributionType | 'new' | null>(null)
  const types = useQuery({ queryKey: keys.types, queryFn: () => contributionTypeService.list(eventId) })
  const toggle = useMutation({
    mutationFn: (ct: ContributionType) => contributionTypeService.update(ct.id, { is_active: !ct.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.types }),
    onError,
  })
  const canManage = can('contribution_types.manage')
  const currency = detail?.organization.currency

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="font-semibold">{t('ctypes.title')}</h2>
          <p className="text-xs text-slate-500">{t('ctypes.help')}</p>
        </div>
        {canManage && (
          <Button size="sm" icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
            {t('ctypes.add')}
          </Button>
        )}
      </div>
      {types.isLoading ? (
        <SkeletonRows rows={2} />
      ) : types.isError ? (
        <ErrorState onRetry={() => void types.refetch()} />
      ) : types.data!.count === 0 ? (
        <EmptyState title={t('ctypes.empty')} message={t('ctypes.emptyMessage')} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {types.data!.results.map((ct) => (
            <li key={ct.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="font-medium">{ct.name}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <Badge tone="brand">{t(`kind.${ct.kind}`)}</Badge>
                  {ct.fund_name && <Badge>{ct.fund_name}</Badge>}
                  {ct.is_mandatory && ct.target_amount && (
                    <Badge tone="amber">
                      {t('ctypes.mandatoryBadge', { amount: formatMoney(ct.target_amount, currency) })}
                    </Badge>
                  )}
                  {(ct.suggested_min || ct.suggested_max) && (
                    <Badge>
                      {t('ctypes.suggestedBadge', {
                        range: [ct.suggested_min, ct.suggested_max].filter(Boolean).map((v) => formatMoney(v, currency)).join(' – '),
                      })}
                    </Badge>
                  )}
                  {!ct.is_active && <Badge>{t('funds.archived')}</Badge>}
                </div>
              </div>
              {canManage && (
                <div className="flex shrink-0">
                  <Button variant="ghost" size="sm" aria-label={t('common.edit')} onClick={() => setEditing(ct)}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={ct.is_active ? t('funds.archive') : t('funds.restore')}
                    onClick={() => toggle.mutate(ct)}
                  >
                    {ct.is_active ? <Archive className="size-4" /> : <ArchiveRestore className="size-4" />}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <ContributionTypeModal
        eventId={eventId}
        ctype={editing === 'new' ? null : editing}
        open={editing !== null}
        onClose={() => setEditing(null)}
      />
    </Card>
  )
}

interface TypeValues {
  name: string
  kind: ContributionKind
  fund: string
  suggested_min: string
  suggested_max: string
  is_mandatory: boolean
  target_amount: string
  start_date: string
  end_date: string
  description: string
}

const TYPE_FIELDS = ['name', 'kind', 'fund', 'suggested_min', 'suggested_max', 'target_amount', 'start_date', 'end_date', 'description']

function ContributionTypeModal({
  eventId,
  ctype,
  open,
  onClose,
}: {
  eventId: string
  ctype: ContributionType | null
  open: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const keys = useEventMoneyKeys(eventId)
  const queryClient = useQueryClient()
  const funds = useQuery({ queryKey: keys.funds, queryFn: () => fundService.list(eventId), enabled: open })
  const { register, handleSubmit, reset, watch, setError, formState } = useForm<TypeValues>()
  const onError = useApiErrors(setError, TYPE_FIELDS)
  const kind = watch('kind')
  const mandatory = watch('is_mandatory')

  useEffect(() => {
    if (!open) return
    reset({
      name: ctype?.name ?? '',
      kind: ctype?.kind ?? 'recurring_monthly',
      fund: ctype?.fund ?? '',
      suggested_min: ctype?.suggested_min ?? '',
      suggested_max: ctype?.suggested_max ?? '',
      is_mandatory: ctype?.is_mandatory ?? false,
      target_amount: ctype?.target_amount ?? '',
      start_date: ctype?.start_date ?? '',
      end_date: ctype?.end_date ?? '',
      description: ctype?.description ?? '',
    })
  }, [open, ctype, reset])

  const onSubmit = handleSubmit(async (values) => {
    const payload: ContributionTypeInput = {
      name: values.name,
      kind: values.kind,
      fund: values.fund || null,
      suggested_min: values.suggested_min || null,
      suggested_max: values.suggested_max || null,
      is_mandatory: values.is_mandatory,
      target_amount: values.target_amount || null,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      description: values.description,
    }
    try {
      if (ctype) await contributionTypeService.update(ctype.id, payload)
      else await contributionTypeService.create({ ...payload, event: eventId })
      await queryClient.invalidateQueries({ queryKey: keys.types })
      notify(t('common.saved'))
      onClose()
    } catch (error) {
      onError(error)
    }
  })

  const moneyError = (field: keyof TypeValues) => {
    const error = formState.errors[field]
    return error && (error.message || t('validation.amount'))
  }
  const activeFunds = (funds.data?.results ?? []).filter((f) => f.is_active || f.id === ctype?.fund)

  return (
    <Modal
      open={open}
      title={ctype ? t('ctypes.edit') : t('ctypes.add')}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="ctype-form" loading={formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form id="ctype-form" onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2" noValidate>
        <TextInput
          className="sm:col-span-2"
          label={t('ctypes.name')}
          placeholder={t('ctypes.namePlaceholder')}
          required
          error={formState.errors.name && (formState.errors.name.message || t('validation.required'))}
          {...register('name', { required: true })}
        />
        <SelectInput label={t('ctypes.kind')} error={formState.errors.kind?.message} {...register('kind')}>
          <option value="recurring_monthly">{t('kind.recurring_monthly')}</option>
          <option value="one_time">{t('kind.one_time')}</option>
        </SelectInput>
        <SelectInput label={t('ctypes.fund')} error={formState.errors.fund?.message} {...register('fund')}>
          <option value="">{t('ctypes.noFund')}</option>
          {activeFunds.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </SelectInput>
        <TextInput label={t('ctypes.suggestedMin')} hint={t('common.optional')} inputMode="decimal" error={moneyError('suggested_min')} {...register('suggested_min', { pattern: MONEY_PATTERN })} />
        <TextInput label={t('ctypes.suggestedMax')} hint={t('common.optional')} inputMode="decimal" error={moneyError('suggested_max')} {...register('suggested_max', { pattern: MONEY_PATTERN })} />
        <div className="sm:col-span-2">
          <Checkbox label={t('ctypes.mandatory')} description={t('ctypes.mandatoryHelp')} {...register('is_mandatory')} />
        </div>
        {mandatory && (
          <TextInput
            className="sm:col-span-2"
            label={kind === 'recurring_monthly' ? t('ctypes.targetMonthly') : t('ctypes.target')}
            required
            inputMode="decimal"
            error={moneyError('target_amount')}
            {...register('target_amount', { required: mandatory, pattern: MONEY_PATTERN })}
          />
        )}
        <TextInput label={t('ctypes.startDate')} type="date" hint={t('common.optional')} error={formState.errors.start_date?.message} {...register('start_date')} />
        <TextInput label={t('ctypes.endDate')} type="date" hint={t('common.optional')} error={formState.errors.end_date?.message} {...register('end_date')} />
        <TextArea className="sm:col-span-2" label={t('ctypes.description')} {...register('description')} />
      </form>
    </Modal>
  )
}

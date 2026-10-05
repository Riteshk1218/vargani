import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Checkbox, SelectInput, TextArea, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { eventService, type EventInput } from '../../services/events'
import { financialYearService } from '../../services/organizations'
import type { EventItem, EventModules, EventTemplateCode } from '../../types/api'

const MODULES = ['contributions', 'monthly', 'expenses', 'collectors', 'member_portal'] as const

interface Values {
  name: string
  template: EventTemplateCode
  financial_year: string
  code: string
  start_date: string
  end_date: string
  target_amount: string
  description: string
  thank_you_message: string
  modules: EventModules
}

export function EventFormModal({ open, event, onClose }: { open: boolean; event?: EventItem | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const { activeOrgId, detail } = useOrg()
  const templates = useQuery({ queryKey: ['org', activeOrgId, 'event-templates'], queryFn: eventService.templates, enabled: open })
  const years = useQuery({ queryKey: ['org', activeOrgId, 'financial-years'], queryFn: financialYearService.list, enabled: open })
  const { register, handleSubmit, reset, setValue, watch, setError, formState } = useForm<Values>()
  const onError = useApiErrors(setError, ['name', 'template', 'financial_year', 'code', 'start_date', 'end_date', 'target_amount', 'description', 'thank_you_message'])
  const template = watch('template')

  useEffect(() => {
    if (!open) return
    reset({
      name: event?.name ?? '',
      template: event?.template ?? 'festival',
      financial_year: event?.financial_year ?? detail?.current_financial_year?.id ?? '',
      code: event?.code ?? '',
      start_date: event?.start_date ?? '',
      end_date: event?.end_date ?? '',
      target_amount: event?.target_amount ?? '',
      description: event?.description ?? '',
      thank_you_message: event?.thank_you_message ?? '',
      modules: event?.modules ?? {},
    })
  }, [open, event, detail, reset])

  // New events start from the chosen template's modules.
  useEffect(() => {
    if (event || !templates.data || !template) return
    const chosen = templates.data.find((item) => item.code === template)
    if (chosen) setValue('modules', { ...chosen.modules })
  }, [template, templates.data, event, setValue])

  const onSubmit = async (values: Values) => {
    const payload: EventInput = {
      name: values.name,
      code: values.code,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      target_amount: values.target_amount || null,
      description: values.description,
      thank_you_message: values.thank_you_message,
      modules: values.modules,
    }
    try {
      if (event) await eventService.update(event.id, payload)
      else await eventService.create({ ...payload, template: values.template, financial_year: values.financial_year })
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'events'] })
      notify(event ? t('common.saved') : t('events.created'))
      onClose()
    } catch (error) {
      onError(error)
    }
  }

  const openYears = (years.data?.results ?? []).filter((year) => year.status === 'open' || year.id === event?.financial_year)
  return (
    <Modal
      open={open}
      title={event ? t('events.edit') : t('events.create')}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="event-form" loading={formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form id="event-form" onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
        <TextInput
          className="sm:col-span-2"
          label={t('events.name')}
          placeholder={t('events.namePlaceholder')}
          required
          error={formState.errors.name && (formState.errors.name.message || t('validation.required'))}
          {...register('name', { required: true })}
        />
        <SelectInput label={t('events.template')} disabled={Boolean(event)} {...register('template')}>
          {(templates.data ?? []).map((item) => (
            <option key={item.code} value={item.code}>
              {item.name}
            </option>
          ))}
        </SelectInput>
        <SelectInput label={t('events.financialYear')} required disabled={Boolean(event)} error={formState.errors.financial_year?.message} {...register('financial_year', { required: true })}>
          {openYears.map((year) => (
            <option key={year.id} value={year.id}>
              {year.label}
            </option>
          ))}
        </SelectInput>
        <TextInput label={t('events.code')} hint={t('events.codeHint')} maxLength={12} error={formState.errors.code?.message} {...register('code')} />
        <TextInput label={t('events.target')} hint={t('events.targetHint')} inputMode="decimal" error={formState.errors.target_amount?.message} {...register('target_amount', { pattern: /^\d+(\.\d{1,2})?$/ })} />
        <TextInput label={t('events.startDate')} type="date" error={formState.errors.start_date?.message} {...register('start_date')} />
        <TextInput label={t('events.endDate')} type="date" error={formState.errors.end_date?.message} {...register('end_date')} />
        <TextArea className="sm:col-span-2" label={t('events.description')} {...register('description')} />
        <TextInput className="sm:col-span-2" label={t('events.thankYou')} hint={t('events.thankYouHint')} maxLength={300} {...register('thank_you_message')} />
        <fieldset className="space-y-3 sm:col-span-2">
          <legend className="text-sm font-medium text-slate-700">{t('events.modules')}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {MODULES.map((module) => (
              <Checkbox key={module} label={t(`events.module.${module}`)} {...register(`modules.${module}` as const)} />
            ))}
          </div>
        </fieldset>
      </form>
    </Modal>
  )
}

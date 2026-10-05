import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Checkbox, TextArea, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { peopleService } from '../../services/people'
import type { Person, PersonType } from '../../types/api'

export const PERSON_TYPES: PersonType[] = ['member', 'karyakarta', 'volunteer', 'donor', 'supporter', 'other']
const FIELDS = ['full_name', 'mobile', 'alt_mobile', 'email', 'unit', 'building', 'area', 'address_line', 'city', 'pincode', 'notes'] as const
type Values = Record<(typeof FIELDS)[number], string> & { person_types: PersonType[] }

export function PersonFormModal({ open, person, onClose }: { open: boolean; person?: Person | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const { activeOrgId } = useOrg()
  const [duplicates, setDuplicates] = useState<{ id: string; full_name: string }[]>([])
  const { register, handleSubmit, reset, setError, formState } = useForm<Values>()
  const onError = useApiErrors(setError, [...FIELDS, 'person_types'])

  useEffect(() => {
    if (!open) return
    setDuplicates([])
    const values = Object.fromEntries(FIELDS.map((field) => [field, person?.[field] ?? ''])) as unknown as Values
    values.person_types = person?.person_types ?? ['member']
    reset(values)
  }, [open, person, reset])

  const checkMobile = async (mobile: string) => {
    if (mobile.replace(/\D/g, '').length < 10) return setDuplicates([])
    try {
      const matches = await peopleService.checkDuplicates(mobile)
      setDuplicates(matches.filter((match) => match.id !== person?.id))
    } catch {
      setDuplicates([])
    }
  }

  const onSubmit = async (values: Values) => {
    try {
      if (person) await peopleService.update(person.id, values)
      else await peopleService.create(values)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'people'] })
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'dashboard'] })
      notify(person ? t('common.saved') : t('people.added'))
      onClose()
    } catch (error) {
      onError(error)
    }
  }

  return (
    <Modal
      open={open}
      title={person ? t('people.edit') : t('people.add')}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="person-form" loading={formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form id="person-form" onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
        <TextInput
          className="sm:col-span-2"
          label={t('people.fullName')}
          required
          error={formState.errors.full_name && (formState.errors.full_name.message || t('validation.required'))}
          {...register('full_name', { required: true, validate: (v) => v.trim().length > 0 })}
        />
        <div>
          <TextInput
            label={t('people.mobile')}
            type="tel"
            inputMode="tel"
            error={formState.errors.mobile?.message}
            {...register('mobile', { onBlur: (e) => void checkMobile(e.target.value) })}
          />
          {duplicates.length > 0 && (
            <p className="mt-1 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">
              {t('people.duplicateWarning', { names: duplicates.map((d) => d.full_name).join(', ') })}
            </p>
          )}
        </div>
        <TextInput label={t('people.altMobile')} type="tel" inputMode="tel" error={formState.errors.alt_mobile?.message} {...register('alt_mobile')} />
        <TextInput label={t('people.email')} type="email" error={formState.errors.email?.message} {...register('email')} />
        <TextInput label={t('people.unit')} error={formState.errors.unit?.message} {...register('unit')} />
        <TextInput label={t('people.building')} {...register('building')} />
        <TextInput label={t('people.area')} {...register('area')} />
        <TextInput className="sm:col-span-2" label={t('people.address')} {...register('address_line')} />
        <TextInput label={t('people.city')} {...register('city')} />
        <TextInput label={t('people.pincode')} inputMode="numeric" maxLength={10} {...register('pincode')} />
        <fieldset className="space-y-2 sm:col-span-2">
          <legend className="text-sm font-medium text-slate-700">{t('people.types')}</legend>
          <p className="text-xs text-slate-500">{t('people.typesHint')}</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {PERSON_TYPES.map((type) => (
              <Checkbox key={type} label={t(`personType.${type}`)} value={type} {...register('person_types')} />
            ))}
          </div>
        </fieldset>
        <TextArea className="sm:col-span-2" label={t('people.notes')} {...register('notes')} />
      </form>
    </Modal>
  )
}

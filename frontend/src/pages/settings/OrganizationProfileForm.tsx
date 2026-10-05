import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { SelectInput, TextArea, TextInput } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { LANGUAGES } from '../../i18n'
import { organizationService } from '../../services/organizations'
import type { Organization } from '../../types/api'

const FIELDS = [
  'name', 'address_line1', 'address_line2', 'city', 'district', 'state', 'pincode', 'country', 'phone', 'email', 'website',
  'description', 'registration_type', 'registration_number', 'default_language', 'receipt_language',
] as const
type Values = Pick<Organization, (typeof FIELDS)[number]>

export function OrganizationProfileForm({ organization }: { organization: Organization }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const { activeOrgId } = useOrg()
  const { register, handleSubmit, reset, setError, formState } = useForm<Values>()
  const onError = useApiErrors(setError, [...FIELDS])

  useEffect(() => {
    reset(Object.fromEntries(FIELDS.map((field) => [field, organization[field] ?? ''])) as Values)
  }, [organization, reset])

  const onSubmit = async (values: Values) => {
    try {
      await organizationService.update(organization.id, values)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'me'] })
      await queryClient.invalidateQueries({ queryKey: ['me', 'organizations'] })
      notify(t('common.saved'))
    } catch (error) {
      onError(error)
    }
  }
  const text = (field: (typeof FIELDS)[number], label: string, extra: Record<string, unknown> = {}) => (
    <TextInput label={label} error={formState.errors[field]?.message} {...extra} {...register(field)} />
  )

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
      <TextInput
        className="sm:col-span-2"
        label={t('organization.name')}
        required
        error={formState.errors.name && (formState.errors.name.message || t('validation.required'))}
        {...register('name', { required: true })}
      />
      {text('address_line1', t('organization.address1'))}
      {text('address_line2', t('organization.address2'))}
      {text('city', t('organization.city'))}
      {text('district', t('organization.district'))}
      {text('state', t('organization.state'))}
      {text('pincode', t('organization.pincode'), { inputMode: 'numeric' })}
      {text('phone', t('organization.phone'), { type: 'tel' })}
      {text('email', t('organization.email'), { type: 'email' })}
      {text('website', t('organization.website'), { type: 'url', placeholder: 'https://' })}
      {text('country', t('organization.country'))}
      {text('registration_type', t('organization.registrationType'), { placeholder: t('organization.registrationTypePlaceholder') })}
      {text('registration_number', t('organization.registrationNumber'))}
      <SelectInput label={t('organization.defaultLanguage')} {...register('default_language')}>
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </SelectInput>
      <SelectInput label={t('organization.receiptLanguage')} hint={t('organization.receiptLanguageHint')} {...register('receipt_language')}>
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </SelectInput>
      <TextArea className="sm:col-span-2" label={t('organization.description')} {...register('description')} />
      <div className="sm:col-span-2">
        <Button type="submit" loading={formState.isSubmitting}>
          {t('common.save')}
        </Button>
      </div>
    </form>
  )
}

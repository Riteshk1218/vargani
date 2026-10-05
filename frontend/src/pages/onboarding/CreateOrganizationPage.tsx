import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { organizationService } from '../../services/organizations'
import { suggestFinancialYear } from '../../utils/format'

interface Values {
  name: string
  city: string
  phone: string
  fy_label: string
  fy_start: string
  fy_end: string
}

export function CreateOrganizationPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { memberships, switchOrganization } = useOrg()
  const fy = suggestFinancialYear()
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    defaultValues: { name: '', city: '', phone: '', fy_label: fy.label, fy_start: fy.start_date, fy_end: fy.end_date },
  })
  const onError = useApiErrors(setError, ['name', 'city', 'phone'])

  const onSubmit = async (values: Values) => {
    try {
      const org = await organizationService.create({
        name: values.name,
        city: values.city,
        phone: values.phone,
        financial_year: { label: values.fy_label, start_date: values.fy_start, end_date: values.fy_end },
      })
      await queryClient.invalidateQueries({ queryKey: ['me', 'organizations'] })
      switchOrganization(org.id)
      navigate('/app/dashboard', { replace: true })
    } catch (error) {
      onError(error)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <h1 className="text-xl font-semibold">{t('onboarding.title')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('onboarding.subtitle')}</p>
      </div>
      <TextInput
        label={t('organization.name')}
        placeholder={t('onboarding.namePlaceholder')}
        required
        error={formState.errors.name && (formState.errors.name.message || t('validation.required'))}
        {...register('name', { required: true, validate: (v) => v.trim().length > 0 })}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput label={t('organization.city')} error={formState.errors.city?.message} {...register('city')} />
        <TextInput label={t('organization.phone')} type="tel" error={formState.errors.phone?.message} {...register('phone')} />
      </div>
      <fieldset className="space-y-3 rounded-xl bg-slate-50 p-4">
        <legend className="px-1 text-sm font-medium text-slate-700">{t('onboarding.financialYear')}</legend>
        <TextInput label={t('financialYears.label')} required {...register('fy_label', { required: true })} />
        <div className="grid grid-cols-2 gap-3">
          <TextInput label={t('financialYears.start')} type="date" required {...register('fy_start', { required: true })} />
          <TextInput label={t('financialYears.end')} type="date" required {...register('fy_end', { required: true })} />
        </div>
      </fieldset>
      <p className="text-xs text-slate-500">{t('onboarding.adminNote')}</p>
      <Button type="submit" className="w-full" loading={formState.isSubmitting}>
        {t('onboarding.create')}
      </Button>
      {memberships.length > 0 && (
        <Button variant="ghost" className="w-full" onClick={() => navigate('/app/dashboard')}>
          {t('common.cancel')}
        </Button>
      )}
    </form>
  )
}

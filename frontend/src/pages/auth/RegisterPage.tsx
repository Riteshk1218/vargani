import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useApiErrors } from '../../hooks/useApiErrors'
import { authService } from '../../services/auth'
import type { Language } from '../../types/api'

const schema = z
  .object({
    full_name: z.string().trim().min(2),
    email: z.union([z.literal(''), z.email()]),
    mobile: z.string().trim(),
    password: z.string().min(10),
  })
  .refine((v) => v.email || v.mobile, { path: ['email'], message: 'identifier' })
type Values = z.infer<typeof schema>

export function RegisterPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: '', email: '', mobile: '', password: '' },
  })
  const onError = useApiErrors(setError, ['full_name', 'email', 'mobile', 'password'])
  const errors = formState.errors

  const onSubmit = async (values: Values) => {
    try {
      const response = await authService.register({
        full_name: values.full_name,
        email: values.email || undefined,
        mobile: values.mobile || undefined,
        password: values.password,
        preferred_language: i18n.language as Language,
      })
      navigate('/verify', { state: { destination: values.email || values.mobile, masked: response.verification.destination, debugCode: response.debug_code } })
    } catch (error) {
      onError(error)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <h1 className="text-xl font-semibold">{t('auth.registerTitle')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('auth.registerSubtitle')}</p>
      </div>
      <TextInput label={t('auth.fullName')} autoComplete="name" required error={errors.full_name && (errors.full_name.message?.length ? errors.full_name.message : t('validation.required'))} {...register('full_name')} />
      <TextInput
        label={t('auth.email')}
        type="email"
        autoComplete="email"
        error={errors.email && (errors.email.message === 'identifier' ? t('auth.identifierRequired') : errors.email.message || t('validation.email'))}
        {...register('email')}
      />
      <TextInput label={t('auth.mobile')} type="tel" inputMode="tel" autoComplete="tel" placeholder="98XXXXXXXX" error={errors.mobile?.message} {...register('mobile')} />
      <TextInput
        label={t('auth.password')}
        type="password"
        autoComplete="new-password"
        required
        hint={t('auth.passwordHint')}
        error={errors.password && (errors.password.type === 'server' ? errors.password.message : t('auth.passwordHint'))}
        {...register('password')}
      />
      <Button type="submit" className="w-full" loading={formState.isSubmitting}>
        {t('auth.createAccount')}
      </Button>
      <p className="text-center text-sm text-slate-600">
        {t('auth.haveAccount')}{' '}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          {t('auth.login')}
        </Link>
      </p>
    </form>
  )
}

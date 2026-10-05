import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useAuth } from '../../context/AuthContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { authService } from '../../services/auth'
import { toApiError } from '../../services/apiClient'
import { MEMBER_LOGIN_KEY, session } from '../../services/session'

const schema = z.object({ identifier: z.string().trim().min(1), password: z.string().min(1) })
type Values = z.infer<typeof schema>

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { startSession } = useAuth()
  const { register, handleSubmit, setError, formState } = useForm<Values>({ resolver: zodResolver(schema) })
  const onError = useApiErrors(setError, ['identifier', 'password'])

  const onSubmit = async (values: Values) => {
    try {
      startSession(await authService.login(values.identifier, values.password))
      session.write(MEMBER_LOGIN_KEY, null)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && (from.startsWith('/app') || from.startsWith('/invite/')) ? from : '/app/dashboard', { replace: true })
    } catch (error) {
      const apiError = toApiError(error)
      if (apiError.code === 'verification_required') {
        await authService.resendVerification(values.identifier).catch(() => undefined)
        navigate('/verify', { state: { destination: values.identifier } })
        return
      }
      if (apiError.code === 'validation_error' && !Object.keys(apiError.details).some((k) => k !== 'non_field_errors')) {
        setError('password', { type: 'server', message: apiError.message })
        return
      }
      onError(error)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div>
        <h1 className="text-xl font-semibold">{t('auth.loginTitle')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('auth.loginSubtitle')}</p>
      </div>
      <TextInput
        label={t('auth.identifier')}
        autoComplete="username"
        inputMode="email"
        required
        error={formState.errors.identifier && (formState.errors.identifier.message || t('validation.required'))}
        {...register('identifier')}
      />
      <TextInput
        label={t('auth.password')}
        type="password"
        autoComplete="current-password"
        required
        error={formState.errors.password && (formState.errors.password.message || t('validation.required'))}
        {...register('password')}
      />
      <div className="flex justify-end">
        <Link to="/forgot-password" className="text-sm font-medium text-brand-700 hover:underline">
          {t('auth.forgotPassword')}
        </Link>
      </div>
      <Button type="submit" className="w-full" loading={formState.isSubmitting}>
        {t('auth.login')}
      </Button>
      <p className="text-center text-sm text-slate-600">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className="font-medium text-brand-700 hover:underline">
          {t('auth.registerLink')}
        </Link>
      </p>
      <Link to="/member-login" className="block rounded-lg border border-slate-200 px-3 py-2.5 text-center text-sm font-medium text-slate-700 hover:bg-slate-50">
        {t('memberLogin.link')}
      </Link>
    </form>
  )
}

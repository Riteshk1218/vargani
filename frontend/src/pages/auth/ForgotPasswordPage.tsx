import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { useApiErrors } from '../../hooks/useApiErrors'
import { authService } from '../../services/auth'

interface Values {
  identifier: string
  code: string
  new_password: string
}

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [step, setStep] = useState<'request' | 'reset'>('request')
  const [debugCode, setDebugCode] = useState<string>()
  const { register, handleSubmit, setError, getValues, formState } = useForm<Values>({ defaultValues: { identifier: '', code: '', new_password: '' } })
  const onError = useApiErrors(setError, ['identifier', 'code', 'new_password'])

  const onSubmit = async (values: Values) => {
    try {
      if (step === 'request') {
        const response = await authService.forgotPassword(values.identifier)
        setDebugCode(response.debug_code)
        setStep('reset')
      } else {
        await authService.resetPassword(getValues('identifier'), values.code.trim(), values.new_password)
        notify(t('auth.passwordResetDone'))
        navigate('/login')
      }
    } catch (error) {
      onError(error)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div>
        <h1 className="text-xl font-semibold">{t('auth.resetTitle')}</h1>
        <p className="mt-1 text-sm text-slate-500">{step === 'request' ? t('auth.resetSubtitle') : t('auth.resetCodeSent')}</p>
      </div>
      <TextInput label={t('auth.identifier')} required disabled={step === 'reset'} error={formState.errors.identifier?.message} {...register('identifier', { required: true })} />
      {step === 'reset' && (
        <>
          {debugCode && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{t('auth.devCode', { code: debugCode })}</p>}
          <TextInput label={t('auth.code')} inputMode="numeric" autoComplete="one-time-code" required error={formState.errors.code?.message} {...register('code', { required: true })} />
          <TextInput
            label={t('auth.newPassword')}
            type="password"
            autoComplete="new-password"
            required
            hint={t('auth.passwordHint')}
            error={formState.errors.new_password?.message}
            {...register('new_password', { required: true })}
          />
        </>
      )}
      <Button type="submit" className="w-full" loading={formState.isSubmitting}>
        {step === 'request' ? t('auth.sendCode') : t('auth.setNewPassword')}
      </Button>
      <p className="text-center text-sm">
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          {t('auth.backToLogin')}
        </Link>
      </p>
    </form>
  )
}

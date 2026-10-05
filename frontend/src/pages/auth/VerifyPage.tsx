import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { authService } from '../../services/auth'

interface VerifyState {
  destination?: string
  masked?: string
  debugCode?: string
}

export function VerifyPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { notify } = useToast()
  const { startSession } = useAuth()
  const state = (useLocation().state ?? {}) as VerifyState
  const [debugCode, setDebugCode] = useState(state.debugCode)
  const { register, handleSubmit, setError, formState } = useForm<{ code: string }>({ defaultValues: { code: '' } })
  const onError = useApiErrors(setError, ['code'])
  const [resending, setResending] = useState(false)

  if (!state.destination) return <Navigate to="/login" replace />

  const onSubmit = async ({ code }: { code: string }) => {
    try {
      startSession(await authService.verify(state.destination!, code.trim()))
      navigate('/app/dashboard', { replace: true })
    } catch (error) {
      onError(error)
    }
  }

  const resend = async () => {
    setResending(true)
    try {
      const response = await authService.resendVerification(state.destination!)
      setDebugCode(response.debug_code)
      notify(t('auth.codeResent'))
    } catch (error) {
      onError(error)
    } finally {
      setResending(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div>
        <h1 className="text-xl font-semibold">{t('auth.verifyTitle')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('auth.verifySubtitle', { destination: state.masked ?? state.destination })}</p>
      </div>
      {debugCode && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{t('auth.devCode', { code: debugCode })}</p>}
      <TextInput
        label={t('auth.code')}
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        required
        error={formState.errors.code?.message}
        {...register('code', { required: true })}
      />
      <Button type="submit" className="w-full" loading={formState.isSubmitting}>
        {t('auth.verify')}
      </Button>
      <Button variant="ghost" className="w-full" loading={resending} onClick={() => void resend()}>
        {t('auth.resendCode')}
      </Button>
    </form>
  )
}

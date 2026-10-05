import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { TextInput } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { toApiError } from '../../services/apiClient'
import { memberAuthService } from '../../services/portal'
import { MEMBER_LOGIN_KEY, session } from '../../services/session'

/** Members log in with their mobile number and a one-time code. No password to remember. */
export function MemberLoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { notify } = useToast()
  const { startSession } = useAuth()
  const [mobile, setMobile] = useState('')
  const [code, setCode] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [debugCode, setDebugCode] = useState<string | undefined>()
  const [error, setError] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)

  const requestCode = async () => {
    setError(undefined)
    if (!mobile.trim()) return setError(t('validation.required'))
    setBusy(true)
    try {
      const response = await memberAuthService.requestCode(mobile.trim())
      setSentTo(response.verification.destination)
      setDebugCode(response.debug_code)
      setCode('')
    } catch (err) {
      const apiError = toApiError(err)
      setError(apiError.details.mobile?.[0] ?? apiError.message)
    } finally {
      setBusy(false)
    }
  }

  const verify = async () => {
    setError(undefined)
    if (!code.trim()) return setError(t('validation.required'))
    setBusy(true)
    try {
      const tokens = await memberAuthService.verifyCode(mobile.trim(), code.trim())
      session.write(MEMBER_LOGIN_KEY, '1')
      startSession(tokens)
      navigate('/app/my', { replace: true })
    } catch (err) {
      const apiError = toApiError(err)
      setError(apiError.details.code?.[0] ?? apiError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        void (sentTo ? verify() : requestCode())
      }}
    >
      <div>
        <h1 className="text-xl font-semibold">{t('memberLogin.title')}</h1>
        <p className="mt-1 text-sm text-slate-500">{sentTo ? t('auth.verifySubtitle', { destination: sentTo }) : t('memberLogin.subtitle')}</p>
      </div>
      {!sentTo ? (
        <TextInput
          label={t('memberLogin.mobile')}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          required
          value={mobile}
          error={error}
          onChange={(e) => setMobile(e.target.value)}
        />
      ) : (
        <>
          {debugCode && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{t('auth.devCode', { code: debugCode })}</p>}
          <TextInput
            label={t('auth.code')}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            required
            autoFocus
            value={code}
            error={error}
            onChange={(e) => setCode(e.target.value)}
          />
        </>
      )}
      <Button type="submit" className="w-full" loading={busy}>
        {sentTo ? t('auth.verify') : t('memberLogin.sendCode')}
      </Button>
      {sentTo && (
        <div className="flex justify-between text-sm">
          <button type="button" className="font-medium text-brand-700 hover:underline" onClick={() => (setSentTo(null), setError(undefined))}>
            {t('memberLogin.changeNumber')}
          </button>
          <button
            type="button"
            className="font-medium text-brand-700 hover:underline"
            onClick={() => void requestCode().then(() => notify(t('auth.codeResent')))}
          >
            {t('auth.resendCode')}
          </button>
        </div>
      )}
      <p className="text-center text-sm text-slate-600">
        {t('memberLogin.staff')}{' '}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          {t('memberLogin.staffLink')}
        </Link>
      </p>
    </form>
  )
}

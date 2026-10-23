import { Copy, KeyRound, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from './ui/Button'
import { TextInput } from './ui/Field'
import { useToast } from './ui/Toast'

const LETTERS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ'
const DIGITS = '23456789'

/** An easy-to-read password the admin can share, e.g. "Kmrt-4829-Pqws". */
export function generatePassword(): string {
  const pick = (chars: string, n: number) => {
    const values = crypto.getRandomValues(new Uint32Array(n))
    return Array.from(values, (v) => chars[v % chars.length]).join('')
  }
  return `${pick(LETTERS, 4)}-${pick(DIGITS, 4)}-${pick(LETTERS, 4)}`
}

/** Password box with a "Make one" button; the text stays visible so the admin can copy it. */
export function PasswordField({ value, onChange, error, label }: { value: string; onChange: (value: string) => void; error?: string; label?: string }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-1">
      <TextInput
        label={label ?? t('auth.password')}
        required
        autoComplete="new-password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        error={error}
        hint={t('loginDetails.passwordHint')}
      />
      <Button variant="ghost" size="sm" icon={<KeyRound className="size-4" />} onClick={() => onChange(generatePassword())}>
        {t('loginDetails.generate')}
      </Button>
    </div>
  )
}

/** After creating a login: show it once and let the admin copy it or send it on WhatsApp. */
export function LoginShareCard({ name, organization, identifier, mobile, password }: { name: string; organization?: string; identifier: string; mobile?: string | null; password: string }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const [shown] = useState(() => window.location.origin)
  const message = t('loginDetails.message', { name, organization: organization ?? '', site: shown, login: identifier, password })
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-lg bg-slate-50 p-3 text-sm">
        <dt className="text-slate-500">{t('loginDetails.site')}</dt>
        <dd className="break-all font-medium">{shown}</dd>
        <dt className="text-slate-500">{t('loginDetails.login')}</dt>
        <dd className="break-all font-medium">{identifier}</dd>
        <dt className="text-slate-500">{t('auth.password')}</dt>
        <dd className="break-all font-mono font-medium">{password}</dd>
      </dl>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          icon={<Copy className="size-4" />}
          onClick={async () => {
            await navigator.clipboard.writeText(message)
            notify(t('common.copied'))
          }}
        >
          {t('loginDetails.copy')}
        </Button>
        <a
          href={`https://wa.me/${(mobile ?? '').replace(/\D/g, '')}?text=${encodeURIComponent(message)}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-medium text-white hover:bg-emerald-700"
        >
          <MessageCircle className="size-4" /> {t('users.shareWhatsApp')}
        </a>
      </div>
      <p className="text-xs text-slate-500">{t('loginDetails.once')}</p>
    </div>
  )
}

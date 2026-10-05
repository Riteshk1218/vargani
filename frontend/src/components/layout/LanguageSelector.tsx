import { Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../context/AuthContext'
import { LANGUAGES } from '../../i18n'
import { authService } from '../../services/auth'
import { session } from '../../services/session'
import type { Language } from '../../types/api'

/** One global language selector. The choice is saved on the user's profile and in this browser. */
export function LanguageSelector({ compact = false }: { compact?: boolean }) {
  const { t, i18n } = useTranslation()
  const { status, setUser } = useAuth()
  const change = async (language: Language) => {
    await i18n.changeLanguage(language)
    session.setLanguage(language)
    if (status === 'authenticated') {
      try {
        setUser(await authService.updateMe({ preferred_language: language }))
      } catch {
        /* the language still applies locally */
      }
    }
  }
  return (
    <label className="flex items-center gap-1.5 rounded-lg bg-white px-2 ring-1 ring-slate-200">
      <Languages className="size-4 text-slate-400" aria-hidden />
      <span className="sr-only">{t('topbar.language')}</span>
      <select
        value={i18n.language}
        onChange={(e) => void change(e.target.value as Language)}
        className={`h-9 border-0 bg-transparent py-0 pl-0 pr-7 text-sm focus:ring-0 ${compact ? 'max-w-[6.5rem]' : ''}`}
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </label>
  )
}

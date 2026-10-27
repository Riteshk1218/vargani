import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router-dom'
import { LanguageSelector } from '../components/layout/LanguageSelector'

export function AuthLayout() {
  const { t } = useTranslation()
  return (
    <div className="relative flex min-h-full flex-col overflow-hidden bg-gradient-to-b from-brand-50 to-slate-50">
      <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-brand-200/50 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute -bottom-32 -left-24 size-96 rounded-full bg-brand-100/70 blur-3xl" aria-hidden />
      <header className="relative flex items-center justify-between px-4 py-4 sm:px-8">
        <span className="flex items-center gap-2 text-lg font-semibold text-brand-800">
          <span className="inline-flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white shadow-sm" aria-hidden>
            ₹
          </span>
          {t('app.name')}
        </span>
        <LanguageSelector />
      </header>
      <main className="relative flex flex-1 items-start justify-center px-4 pb-12 pt-4 sm:items-center">
        <div className="w-full max-w-md animate-pop-in rounded-2xl bg-white/95 p-6 shadow-xl shadow-brand-900/5 ring-1 ring-slate-200 backdrop-blur sm:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router-dom'
import { LanguageSelector } from '../components/layout/LanguageSelector'

export function AuthLayout() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-full flex-col bg-gradient-to-b from-brand-50 to-slate-50">
      <header className="flex items-center justify-between px-4 py-4 sm:px-8">
        <span className="flex items-center gap-2 text-lg font-semibold text-brand-800">
          <img src="/favicon.svg" alt="" className="size-8" /> {t('app.name')}
        </span>
        <LanguageSelector />
      </header>
      <main className="flex flex-1 items-start justify-center px-4 pb-12 pt-4 sm:items-center">
        <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

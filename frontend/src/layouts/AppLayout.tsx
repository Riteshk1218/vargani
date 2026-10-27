import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet, useLocation } from 'react-router-dom'
import { EventSwitcher } from '../components/layout/EventSwitcher'
import { LanguageSelector } from '../components/layout/LanguageSelector'
import { NotificationBell } from '../components/layout/NotificationBell'
import { Sidebar } from '../components/layout/Sidebar'
import { UserMenu } from '../components/layout/UserMenu'
import { Badge } from '../components/ui/Card'
import { FullPageSpinner } from '../components/ui/States'
import { EventProvider } from '../context/EventContext'
import { useOrg } from '../context/OrgContext'

export function AppLayout() {
  const { t } = useTranslation()
  const { detail, detailLoading } = useOrg()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()
  if (detailLoading || !detail) return <FullPageSpinner />
  const fy = detail.current_financial_year
  return (
    <EventProvider>
      <div className="flex h-full">
        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white/90 backdrop-blur lg:block print:hidden">
          <div className="h-1 bg-gradient-to-r from-brand-700 via-brand-500 to-brand-300" aria-hidden />
          <Sidebar />
        </aside>
        {drawerOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 animate-fade-in bg-slate-900/40 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
            <aside className="absolute inset-y-0 left-0 w-72 animate-pop-in overflow-y-auto bg-white shadow-xl">
              <div className="h-1 bg-gradient-to-r from-brand-700 via-brand-500 to-brand-300" aria-hidden />
              <button type="button" className="absolute right-3 top-3 rounded-md p-1 text-slate-500" onClick={() => setDrawerOpen(false)} aria-label={t('common.close')}>
                <X className="size-5" />
              </button>
              <div className="pt-8">
                <Sidebar onNavigate={() => setDrawerOpen(false)} />
              </div>
            </aside>
          </div>
        )}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex flex-wrap print:hidden items-center gap-2 border-b border-slate-200 bg-white/95 px-3 py-2 backdrop-blur sm:px-6">
            <button type="button" className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setDrawerOpen(true)} aria-label={t('nav.openMenu')}>
              <Menu className="size-5" />
            </button>
            <EventSwitcher />
            {fy && (
              <span className="hidden sm:inline-flex">
                <Badge tone="brand">{t('topbar.financialYear', { label: fy.label })}</Badge>
              </span>
            )}
            <div className="ml-auto flex items-center gap-2">
              <LanguageSelector compact />
              <NotificationBell />
              <UserMenu />
            </div>
          </header>
          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
            <div key={pathname} className="mx-auto max-w-6xl animate-fade-in">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </EventProvider>
  )
}

import { CalendarDays, HandCoins, LayoutDashboard, ListChecks, ReceiptText, Settings, ShieldCheck, Users, Wallet, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'
import { useOrg } from '../../context/OrgContext'
import { cn } from '../../utils/cn'
import { OrgSwitcher } from './OrgSwitcher'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  permission?: string
}

// Expenses, Collectors and Reports are added as their phases ship.
const NAV: NavItem[] = [
  { to: '/app/dashboard', label: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/app/collect', label: 'nav.collect', icon: HandCoins, permission: 'payments.create' },
  { to: '/app/contributions', label: 'nav.contributions', icon: ListChecks, permission: 'contributions.view' },
  { to: '/app/payments', label: 'nav.payments', icon: Wallet, permission: 'payments.view' },
  { to: '/app/receipts', label: 'nav.receipts', icon: ReceiptText, permission: 'receipts.view' },
  { to: '/app/events', label: 'nav.events', icon: CalendarDays, permission: 'events.view' },
  { to: '/app/people', label: 'nav.people', icon: Users, permission: 'people.view' },
  { to: '/app/users', label: 'nav.users', icon: ShieldCheck, permission: 'members.view' },
  { to: '/app/settings', label: 'nav.settings', icon: Settings, permission: 'organization.manage' },
]

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation()
  const { can } = useOrg()
  return (
    <nav className="flex h-full flex-col gap-4 p-3" aria-label={t('nav.main')}>
      <OrgSwitcher />
      <ul className="space-y-1">
        {NAV.filter((item) => !item.permission || can(item.permission)).map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium',
                  isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-700 hover:bg-slate-100',
                )
              }
            >
              <item.icon className="size-4" aria-hidden />
              {t(item.label)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

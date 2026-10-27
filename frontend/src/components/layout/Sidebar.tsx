import { BarChart3, HandHeart, Scale, CalendarDays, HandCoins, History, PiggyBank, Receipt, LayoutDashboard, ListChecks, ReceiptText, Settings, ShieldAlert, ShieldCheck, SlidersHorizontal, Users, UsersRound, Wallet, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'
import { useOrg } from '../../context/OrgContext'
import { cn } from '../../utils/cn'
import { REPORT_PERMISSIONS } from '../../utils/permissions'
import { OrgSwitcher } from './OrgSwitcher'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  permission?: string | string[]
  /** Shown only when the organization has the member portal switched on. */
  portal?: boolean
}

const NAV: NavItem[] = [
  { to: '/app/dashboard', label: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/app/my', label: 'nav.my', icon: HandHeart, permission: 'portal.self', portal: true },
  { to: '/app/collect', label: 'nav.collect', icon: HandCoins, permission: 'payments.create' },
  { to: '/app/contributions', label: 'nav.contributions', icon: ListChecks, permission: 'contributions.view' },
  { to: '/app/payments', label: 'nav.payments', icon: Wallet, permission: 'payments.view' },
  { to: '/app/receipts', label: 'nav.receipts', icon: ReceiptText, permission: 'receipts.view' },
  { to: '/app/collectors', label: 'nav.collectors', icon: UsersRound, permission: 'collectors.manage' },
  { to: '/app/approvals', label: 'nav.approvals', icon: ShieldAlert, permission: 'receipts.void_approve' },
  { to: '/app/expenses', label: 'nav.expenses', icon: Receipt, permission: 'expenses.view' },
  { to: '/app/finance', label: 'nav.finance', icon: Scale, permission: ['dashboard.view_financial', 'reports.view_financial'] },
  { to: '/app/income', label: 'nav.income', icon: PiggyBank, permission: 'other_income.manage' },
  { to: '/app/reports', label: 'nav.reports', icon: BarChart3, permission: REPORT_PERMISSIONS },
  { to: '/app/audit', label: 'nav.audit', icon: History, permission: 'audit.view' },
  { to: '/app/events', label: 'nav.events', icon: CalendarDays, permission: 'events.view' },
  { to: '/app/people', label: 'nav.people', icon: Users, permission: 'people.view' },
  { to: '/app/users', label: 'nav.users', icon: ShieldCheck, permission: 'members.view' },
  { to: '/app/studio', label: 'nav.studio', icon: SlidersHorizontal, permission: 'organization.manage' },
  { to: '/app/settings', label: 'nav.settings', icon: Settings, permission: 'organization.manage' },
]

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation()
  const { can, detail } = useOrg()
  const portalOn = Boolean(detail?.member_portal_enabled)
  return (
    <nav className="flex h-full flex-col gap-4 p-3" aria-label={t('nav.main')}>
      <OrgSwitcher />
      <ul className="space-y-1">
        {NAV.filter((item) => (!item.portal || portalOn) && (!item.permission || [item.permission].flat().some(can))).map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-gradient-to-r from-brand-100 to-brand-50 text-brand-800 shadow-sm before:absolute before:inset-y-1.5 before:left-0 before:w-1 before:rounded-full before:bg-brand-600'
                    : 'text-slate-700 hover:translate-x-0.5 hover:bg-slate-100 hover:text-slate-900',
                )
              }
            >
              <item.icon className="size-4 text-brand-600 transition-transform group-hover:scale-110" aria-hidden />
              {t(item.label)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

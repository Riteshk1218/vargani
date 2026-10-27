import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, PageHeader } from '../../components/ui/Card'
import { useOrg } from '../../context/OrgContext'
import { cn } from '../../utils/cn'
import { FinancialYearsPanel } from './FinancialYearsPanel'
import { LogoUploader } from './LogoUploader'
import { OrganizationProfileForm } from './OrganizationProfileForm'
import { OrganizationSettingsPanel, OrganizationThemePanel } from './OrganizationSettingsPanel'
import { PaymentGatewayPanel } from './PaymentGatewayPanel'

const TABS = ['profile', 'logo', 'appearance', 'financialYears', 'preferences', 'onlinePayments'] as const

export function SettingsPage() {
  const { t } = useTranslation()
  const { detail } = useOrg()
  const [tab, setTab] = useState<(typeof TABS)[number]>('profile')
  const organization = detail!.organization
  return (
    <div>
      <PageHeader title={t('settings.title')} description={organization.name} />
      <div className="mb-4 flex gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1" role="tablist">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn('whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium', 'transition-all', tab === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600 hover:bg-white/60 hover:text-slate-900')}
          >
            {t(`settings.tabs.${key}`)}
          </button>
        ))}
      </div>
      <Card className="p-5">
        {tab === 'profile' && <OrganizationProfileForm organization={organization} />}
        {tab === 'logo' && <LogoUploader organization={organization} />}
        {tab === 'appearance' && <OrganizationThemePanel />}
        {tab === 'financialYears' && <FinancialYearsPanel />}
        {tab === 'preferences' && <OrganizationSettingsPanel />}
        {tab === 'onlinePayments' && <PaymentGatewayPanel />}
      </Card>
    </div>
  )
}

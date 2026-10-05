import { Check, ChevronsUpDown, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useOrg } from '../../context/OrgContext'
import { OrgAvatar } from '../ui/Avatar'
import { Popover } from '../ui/Popover'

export function OrgSwitcher() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { memberships, activeOrgId, switchOrganization, detail } = useOrg()
  const active = memberships.find((m) => m.id === activeOrgId)
  if (!active) return null
  const logo = detail?.organization.id === active.id ? detail.organization.logo_url : active.logo_url
  return (
    <Popover
      label={t('topbar.switchOrganization')}
      trigger={() => (
        <span className="flex min-w-0 items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100">
          <OrgAvatar name={active.name} logoUrl={logo} size="sm" />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{active.name}</span>
            <span className="block truncate text-xs text-slate-500">{t(`roles.${active.role.code}`, active.role.name)}</span>
          </span>
          <ChevronsUpDown className="ml-auto size-4 shrink-0 text-slate-400" />
        </span>
      )}
    >
      {(close) => (
        <div>
          <p className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-slate-500">{t('topbar.yourOrganizations')}</p>
          {memberships.map((m) => (
            <button
              key={m.id}
              type="button"
              role="menuitem"
              onClick={() => {
                switchOrganization(m.id)
                close()
                navigate('/app/dashboard')
              }}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50"
            >
              <OrgAvatar name={m.name} logoUrl={m.logo_url} size="sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{m.name}</span>
                <span className="block truncate text-xs text-slate-500">{t(`roles.${m.role.code}`, m.role.name)}</span>
              </span>
              {m.id === activeOrgId && <Check className="size-4 text-brand-700" />}
            </button>
          ))}
          <div className="my-1 border-t border-slate-100" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              close()
              navigate('/onboarding/create-organization')
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            <Plus className="size-4" /> {t('topbar.createOrganization')}
          </button>
        </div>
      )}
    </Popover>
  )
}

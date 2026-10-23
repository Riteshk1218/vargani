import { LogOut, ShieldCheck, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { initials } from '../../utils/format'
import { Popover } from '../ui/Popover'

export function UserMenu() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null
  return (
    <Popover
      align="right"
      label={t('topbar.profile')}
      trigger={() => (
        <span className="inline-flex size-9 items-center justify-center rounded-full bg-slate-800 text-sm font-semibold text-white">{initials(user.full_name)}</span>
      )}
    >
      {(close) => (
        <div>
          <div className="px-3 py-2">
            <p className="truncate text-sm font-semibold">{user.full_name}</p>
            <p className="truncate text-xs text-slate-500">{user.email ?? user.mobile}</p>
          </div>
          <div className="my-1 border-t border-slate-100" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              close()
              navigate('/app/profile')
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-50"
          >
            <UserRound className="size-4" /> {t('topbar.myProfile')}
          </button>
          {user.is_platform_admin && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                close()
                navigate('/platform')
              }}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-50"
            >
              <ShieldCheck className="size-4" /> {t('platform.title')}
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={async () => {
              close()
              await logout()
              navigate('/login')
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50"
          >
            <LogOut className="size-4" /> {t('common.logout')}
          </button>
        </div>
      )}
    </Popover>
  )
}

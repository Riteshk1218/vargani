import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { EmptyState, FullPageSpinner } from '../components/ui/States'
import { MEMBER_LOGIN_KEY, session } from '../services/session'
import { useAuth } from '../context/AuthContext'
import { useOrg } from '../context/OrgContext'

export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function RedirectIfAuthenticated() {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'authenticated') return <Navigate to="/app/dashboard" replace />
  return <Outlet />
}

/** Users without any organization go to onboarding to create one. */
export function RequireOrganization() {
  const { memberships, membershipsLoading, activeOrgId } = useOrg()
  const { user } = useAuth()
  if (membershipsLoading) return <FullPageSpinner />
  if (memberships.length === 0) {
    // The platform owner runs the platform; they need not belong to any organization.
    if (user?.is_platform_admin) return <Navigate to="/platform" replace />
    // A member who logged in with a code but is not linked to any organization's records yet.
    if (session.read(MEMBER_LOGIN_KEY)) return <NotLinkedYet />
    return <Navigate to="/onboarding/create-organization" replace />
  }
  if (!activeOrgId) return <FullPageSpinner />
  return <Outlet />
}

function NotLinkedYet() {
  const { t } = useTranslation()
  const { logout } = useAuth()
  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <EmptyState
        title={t('portal.portal_not_linked')}
        message={t('portal.notLinkedMessage')}
        action={
          <Button variant="secondary" onClick={() => void logout()}>
            {t('common.logout')}
          </Button>
        }
      />
    </div>
  )
}

/** UX only: the API enforces every permission on its own. */
/** `permission` may be a list, meaning "any of these". */
export function RequirePermission({ permission, children }: { permission: string | string[]; children: ReactNode }) {
  const { t } = useTranslation()
  const { can } = useOrg()
  const codes = Array.isArray(permission) ? permission : [permission]
  if (!codes.some(can)) return <EmptyState title={t('errors.forbiddenTitle')} message={t('errors.forbidden')} />
  return <>{children}</>
}

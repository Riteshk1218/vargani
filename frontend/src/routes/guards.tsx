import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { EmptyState, FullPageSpinner } from '../components/ui/States'
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
  if (membershipsLoading) return <FullPageSpinner />
  if (memberships.length === 0) return <Navigate to="/onboarding/create-organization" replace />
  if (!activeOrgId) return <FullPageSpinner />
  return <Outlet />
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

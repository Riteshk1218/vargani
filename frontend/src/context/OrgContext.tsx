import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { organizationService } from '../services/organizations'
import { session } from '../services/session'
import type { MyOrganization, MyOrganizationDetail } from '../types/api'
import { useAuth } from './AuthContext'

interface OrgValue {
  memberships: MyOrganization[]
  membershipsLoading: boolean
  activeOrgId: string | null
  detail: MyOrganizationDetail | null
  detailLoading: boolean
  switchOrganization: (orgId: string) => void
  can: (permission: string) => boolean
  scope: (permission: string) => string | undefined
}

const OrgContext = createContext<OrgValue | null>(null)

export function OrgProvider({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const queryClient = useQueryClient()
  const [activeOrgId, setActiveOrgId] = useState<string | null>(session.getOrganizationId())

  const membershipsQuery = useQuery({
    queryKey: ['me', 'organizations'],
    queryFn: organizationService.mine,
    enabled: status === 'authenticated',
  })
  const memberships = useMemo(() => membershipsQuery.data ?? [], [membershipsQuery.data])

  // Keep the active organization valid: fall back to the first membership if it was removed.
  useEffect(() => {
    if (!membershipsQuery.data) return
    const stillMember = memberships.some((m) => m.id === activeOrgId)
    if (!stillMember) {
      const next = memberships[0]?.id ?? null
      session.setOrganizationId(next)
      setActiveOrgId(next)
    }
  }, [membershipsQuery.data, memberships, activeOrgId])

  const detailQuery = useQuery({
    queryKey: ['org', activeOrgId, 'me'],
    queryFn: () => organizationService.myDetail(activeOrgId!),
    enabled: status === 'authenticated' && Boolean(activeOrgId) && memberships.some((m) => m.id === activeOrgId),
  })

  const switchOrganization = useCallback(
    (orgId: string) => {
      if (orgId === activeOrgId) return
      session.setOrganizationId(orgId)
      // Drop every cached response from the previous organization so nothing can leak on screen.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' })
      setActiveOrgId(orgId)
    },
    [activeOrgId, queryClient],
  )

  const permissions = detailQuery.data?.permissions
  const can = useCallback((permission: string) => Boolean(permissions && permission in permissions), [permissions])
  const scope = useCallback((permission: string) => permissions?.[permission], [permissions])

  const value = useMemo<OrgValue>(
    () => ({
      memberships,
      membershipsLoading: membershipsQuery.isLoading,
      activeOrgId,
      detail: detailQuery.data ?? null,
      detailLoading: detailQuery.isLoading,
      switchOrganization,
      can,
      scope,
    }),
    [memberships, membershipsQuery.isLoading, activeOrgId, detailQuery.data, detailQuery.isLoading, switchOrganization, can, scope],
  )
  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>
}

export function useOrg() {
  const context = useContext(OrgContext)
  if (!context) throw new Error('useOrg must be used inside OrgProvider')
  return context
}

export function useCan(permission: string) {
  return useOrg().can(permission)
}

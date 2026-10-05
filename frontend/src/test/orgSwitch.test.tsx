import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { vi } from 'vitest'
import { OrgProvider, useOrg } from '../context/OrgContext'
import { session } from '../services/session'

vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ status: 'authenticated' }) }))
vi.mock('../services/organizations', () => ({
  organizationService: {
    mine: vi.fn(async () => [
      { id: 'org-a', name: 'A', logo_url: null, role: { id: 'r1', code: 'org_admin', name: 'Admin' }, membership_id: 'm1' },
      { id: 'org-b', name: 'B', logo_url: null, role: { id: 'r2', code: 'volunteer', name: 'Volunteer' }, membership_id: 'm2' },
    ]),
    myDetail: vi.fn(async (orgId: string) => ({
      organization: { id: orgId, name: orgId },
      membership_id: 'm',
      role: { id: 'r', code: orgId === 'org-a' ? 'org_admin' : 'volunteer', name: '' },
      permissions: orgId === 'org-a' ? { 'members.view': 'all' } : { 'events.view': 'all' },
      current_financial_year: null,
    })),
  },
}))

let api: ReturnType<typeof useOrg>
function Probe() {
  api = useOrg()
  return <span data-testid="active">{api.activeOrgId}</span>
}

function wrapper(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <OrgProvider>{children}</OrgProvider>
    </QueryClientProvider>
  )
}

describe('organization switching', () => {
  it('drops cached data from the previous organization and reloads permissions', async () => {
    session.setOrganizationId('org-a')
    const client = new QueryClient()
    const Wrapper = wrapper(client)
    render(
      <Wrapper>
        <Probe />
      </Wrapper>,
    )
    await waitFor(() => expect(api.can('members.view')).toBe(true))
    client.setQueryData(['org', 'org-a', 'people', 'list'], { count: 1, results: [{ id: 'p1' }] })

    act(() => api.switchOrganization('org-b'))

    await waitFor(() => expect(screen.getByTestId('active').textContent).toBe('org-b'))
    expect(client.getQueryData(['org', 'org-a', 'people', 'list'])).toBeUndefined()
    expect(session.getOrganizationId()).toBe('org-b')
    await waitFor(() => expect(api.can('events.view')).toBe(true))
    expect(api.can('members.view')).toBe(false)
  })
})

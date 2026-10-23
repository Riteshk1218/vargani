import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, KeyRound, Plus, Search, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { LanguageSelector } from '../../components/layout/LanguageSelector'
import { UserMenu } from '../../components/layout/UserMenu'
import { LoginShareCard, PasswordField } from '../../components/LoginDetails'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader, StatCard } from '../../components/ui/Card'
import { TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { useDebounced } from '../../hooks/useDebounced'
import { toApiError } from '../../services/apiClient'
import { platformService } from '../../services/organizations'
import type { PlatformOrganization, PlatformUser } from '../../types/api'
import { cn } from '../../utils/cn'
import { formatDate, formatMobile } from '../../utils/format'

const PAGE_SIZE = 25

/** The platform owner's page: every organization on Vargani and every login, without their money or members. */
export function PlatformPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { memberships } = useOrg()
  const [tab, setTab] = useState<'organizations' | 'users'>('organizations')
  const summary = useQuery({ queryKey: ['platform', 'summary'], queryFn: platformService.summary, enabled: Boolean(user?.is_platform_admin) })

  if (!user?.is_platform_admin) {
    return <EmptyState title={t('errors.forbiddenTitle')} message={t('errors.forbidden')} />
  }
  return (
    <div className="min-h-full bg-slate-50">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-8">
        <span className="flex items-center gap-2 font-semibold text-brand-800">
          <ShieldCheck className="size-5" /> {t('platform.title')}
        </span>
        <div className="flex items-center gap-2">
          {memberships.length > 0 && (
            <Link to="/app/dashboard" className="text-sm font-medium text-brand-700 hover:underline">
              {t('platform.backToApp')}
            </Link>
          )}
          <LanguageSelector />
          <UserMenu />
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-8">
        <PageHeader title={t('platform.title')} description={t('platform.subtitle')} />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label={t('platform.organizations')} value={summary.data?.organizations.total ?? '–'} hint={summary.data ? t('platform.activeSuspended', summary.data.organizations) : undefined} />
          <StatCard label={t('platform.users')} value={summary.data?.users ?? '–'} />
          <StatCard label={t('platform.people')} value={summary.data?.people ?? '–'} />
          <StatCard label={t('platform.receipts')} value={summary.data?.receipts ?? '–'} />
        </div>
        <div className="flex gap-1 border-b border-slate-200" role="tablist">
          {(['organizations', 'users'] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={cn('-mb-px border-b-2 px-4 py-2 text-sm font-medium', tab === key ? 'border-brand-700 text-brand-800' : 'border-transparent text-slate-600 hover:text-slate-900')}
            >
              {t(`platform.${key}`)}
            </button>
          ))}
        </div>
        {tab === 'organizations' ? <OrganizationsTab /> : <UsersTab />}
        <p className="text-xs text-slate-500">{t('platform.privacyNote')}</p>
      </main>
    </div>
  )
}

function SearchBox({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { t } = useTranslation()
  return (
    <label className="relative block w-full sm:max-w-xs">
      <span className="sr-only">{t('common.search')}</span>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('common.search')}
        className="h-10 w-full rounded-lg border-0 pl-9 text-sm ring-1 ring-slate-300"
      />
    </label>
  )
}

function OrganizationsTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(false)
  const debounced = useDebounced(search)
  const orgs = useQuery({
    queryKey: ['platform', 'organizations', debounced, page],
    queryFn: () => platformService.organizations({ search: debounced || undefined, page }),
    placeholderData: keepPreviousData,
  })
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'suspended' }) => platformService.setOrganizationStatus(id, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['platform'] })
      notify(t('common.saved'))
    },
    onError,
  })

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <SearchBox
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
        />
        <Button icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>
          {t('platform.newOrganization')}
        </Button>
      </div>
      <Card>
        {orgs.isLoading ? (
          <SkeletonRows />
        ) : orgs.isError ? (
          <ErrorState onRetry={() => void orgs.refetch()} />
        ) : orgs.data!.count === 0 ? (
          <EmptyState icon={<Building2 className="size-6" />} title={t('platform.noOrganizations')} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {orgs.data!.results.map((org) => (
              <OrganizationRow
                key={org.id}
                org={org}
                busy={setStatus.isPending && setStatus.variables?.id === org.id}
                onStatus={(status) => setStatus.mutate({ id: org.id, status })}
              />
            ))}
          </ul>
        )}
        <Pagination page={page} pageSize={PAGE_SIZE} count={orgs.data?.count ?? 0} onChange={setPage} />
      </Card>
      <CreateOrganizationModal open={creating} onClose={() => setCreating(false)} />
    </div>
  )
}

function OrganizationRow({ org, busy, onStatus }: { org: PlatformOrganization; busy: boolean; onStatus: (status: 'active' | 'suspended') => void }) {
  const { t } = useTranslation()
  return (
    <li className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        {org.logo_url ? (
          <img src={org.logo_url} alt="" className="size-10 shrink-0 rounded-lg object-cover ring-1 ring-slate-200" />
        ) : (
          <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Building2 className="size-5" />
          </span>
        )}
        <div className="min-w-0">
          <p className="font-medium">
            {org.name} {org.status !== 'active' && <Badge tone="amber">{t(`status.${org.status}`, org.status)}</Badge>}
          </p>
          <p className="text-sm text-slate-500">
            {[org.city, t('platform.since', { date: formatDate(org.created_at) })].filter(Boolean).join(' · ')}
          </p>
          <p className="text-sm text-slate-600">
            {t('platform.admin')}:{' '}
            {org.admins.length === 0
              ? '–'
              : org.admins.map((a) => `${a.full_name} (${a.mobile ? formatMobile(a.mobile) : a.email})`).join(', ')}
          </p>
          <p className="text-xs text-slate-500">
            {t('platform.counts', { users: org.users_count, people: org.people_count, events: org.events_count, receipts: org.receipts_count })}
          </p>
        </div>
      </div>
      {org.status !== 'closed' && (
        <Button variant={org.status === 'active' ? 'secondary' : 'primary'} size="sm" loading={busy} onClick={() => onStatus(org.status === 'active' ? 'suspended' : 'active')}>
          {org.status === 'active' ? t('platform.suspend') : t('platform.activate')}
        </Button>
      )}
    </li>
  )
}

interface CreateValues {
  name: string
  city: string
  full_name: string
  mobile: string
  email: string
  password: string
}

function CreateOrganizationModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [created, setCreated] = useState<{ org: PlatformOrganization; password: string } | null>(null)
  const { register, handleSubmit, reset, setError, setValue, watch, formState } = useForm<CreateValues>({
    defaultValues: { name: '', city: '', full_name: '', mobile: '', email: '', password: '' },
  })
  const onError = useApiErrors(setError, ['name', 'city', 'full_name', 'mobile', 'email', 'password'])
  register('password', { required: true })
  const close = () => {
    setCreated(null)
    reset()
    onClose()
  }
  const onSubmit = async (values: CreateValues) => {
    try {
      const org = await platformService.createOrganization({
        name: values.name,
        city: values.city,
        full_name: values.full_name,
        mobile: values.mobile || undefined,
        email: values.email || undefined,
        password: values.password,
      })
      setCreated({ org, password: values.password })
      await queryClient.invalidateQueries({ queryKey: ['platform'] })
    } catch (error) {
      onError(error)
    }
  }
  const admin = created?.org.admins[0]
  const required = (message?: string) => message || t('validation.required')

  return (
    <Modal open={open} title={t('platform.newOrganization')} onClose={close}>
      {created && admin ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{t('platform.created', { name: created.org.name })}</p>
          {created.org.new_login === false ? (
            <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{t('users.addedExisting', { name: admin.full_name })}</p>
          ) : (
            <LoginShareCard
              name={admin.full_name}
              organization={created.org.name}
              identifier={admin.mobile ? formatMobile(admin.mobile) : (admin.email ?? '')}
              mobile={admin.mobile}
              password={created.password}
            />
          )}
          <div className="flex justify-end">
            <Button onClick={close}>{t('common.close')}</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <TextInput label={t('platform.organizationName')} required error={formState.errors.name && required(formState.errors.name.message)} {...register('name', { required: true })} />
          <TextInput label={t('organization.city')} error={formState.errors.city?.message} {...register('city')} />
          <h3 className="border-t border-slate-200 pt-4 text-sm font-semibold">{t('platform.firstAdmin')}</h3>
          <TextInput label={t('users.name')} required error={formState.errors.full_name && required(formState.errors.full_name.message)} {...register('full_name', { required: true })} />
          <TextInput label={t('auth.mobile')} type="tel" inputMode="tel" error={formState.errors.mobile?.message} {...register('mobile')} />
          <TextInput label={t('auth.email')} type="email" error={formState.errors.email?.message} {...register('email')} />
          <p className="text-xs text-slate-500">{t('users.addHint')}</p>
          <PasswordField
            value={watch('password')}
            onChange={(value) => setValue('password', value, { shouldValidate: formState.isSubmitted })}
            error={formState.errors.password && required(formState.errors.password.message)}
          />
          {formState.errors.root && <p className="text-sm text-red-600">{formState.errors.root.message}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={close}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" loading={formState.isSubmitting}>
              {t('platform.create')}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

function UsersTab() {
  const { t } = useTranslation()
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [passwordFor, setPasswordFor] = useState<PlatformUser | null>(null)
  const debounced = useDebounced(search)
  const users = useQuery({
    queryKey: ['platform', 'users', debounced, page],
    queryFn: () => platformService.users({ search: debounced || undefined, page }),
    placeholderData: keepPreviousData,
  })
  const setActive = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => platformService.setUserActive(id, active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['platform', 'users'] })
      notify(t('common.saved'))
    },
    onError,
  })

  return (
    <div className="space-y-3">
      <SearchBox
        value={search}
        onChange={(value) => {
          setSearch(value)
          setPage(1)
        }}
      />
      <Card>
        {users.isLoading ? (
          <SkeletonRows />
        ) : users.isError ? (
          <ErrorState onRetry={() => void users.refetch()} />
        ) : users.data!.count === 0 ? (
          <EmptyState title={t('platform.noUsers')} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {users.data!.results.map((row) => (
              <li key={row.id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {row.full_name} {row.is_platform_admin && <Badge tone="brand">{t('platform.owner')}</Badge>}{' '}
                    {!row.is_active && <Badge tone="amber">{t('platform.blocked')}</Badge>}
                  </p>
                  <p className="truncate text-sm text-slate-500">{[row.mobile && formatMobile(row.mobile), row.email].filter(Boolean).join(' · ')}</p>
                  <p className="text-sm text-slate-600">
                    {row.organizations.length === 0
                      ? t('platform.noOrganization')
                      : row.organizations.map((m) => `${m.name} – ${t(`roles.${m.role.code}`, m.role.name)}${m.status !== 'active' ? ` (${t(`status.${m.status}`)})` : ''}`).join(', ')}
                  </p>
                  <p className="text-xs text-slate-500">
                    {t('platform.lastLogin', { date: row.last_login ? formatDate(row.last_login) : '–' })}
                  </p>
                </div>
                {row.id !== me?.id && (
                  <div className="flex flex-wrap gap-2">
                    <Button variant="ghost" size="sm" icon={<KeyRound className="size-4" />} onClick={() => setPasswordFor(row)}>
                      {t('users.setPassword')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={setActive.isPending && setActive.variables?.id === row.id}
                      onClick={() => setActive.mutate({ id: row.id, active: !row.is_active })}
                    >
                      {row.is_active ? t('platform.block') : t('platform.unblock')}
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        <Pagination page={page} pageSize={PAGE_SIZE} count={users.data?.count ?? 0} onChange={setPage} />
      </Card>
      <UserPasswordModal user={passwordFor} onClose={() => setPasswordFor(null)} />
    </div>
  )
}

function UserPasswordModal({ user, onClose }: { user: PlatformUser | null; onClose: () => void }) {
  const { t } = useTranslation()
  const [password, setPassword] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setFieldError] = useState<string | undefined>()
  const onError = useApiErrors()
  const save = useMutation({
    mutationFn: () => platformService.setUserPassword(user!.id, password),
    onSuccess: () => setSaved(true),
    onError: (err) => {
      const message = toApiError(err).fieldError('password')
      if (message) setFieldError(message)
      else onError(err)
    },
  })
  const close = () => {
    setPassword('')
    setSaved(false)
    setFieldError(undefined)
    onClose()
  }
  if (!user) return null
  return (
    <Modal open title={t('users.setPasswordFor', { name: user.full_name })} onClose={close}>
      {saved ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{t('users.passwordSet')}</p>
          <LoginShareCard
            name={user.full_name}
            organization={user.organizations[0]?.name}
            identifier={user.mobile ? formatMobile(user.mobile) : (user.email ?? '')}
            mobile={user.mobile}
            password={password}
          />
          <div className="flex justify-end">
            <Button onClick={close}>{t('common.close')}</Button>
          </div>
        </div>
      ) : (
        <form
          className="space-y-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            if (!password) return setFieldError(t('validation.required'))
            save.mutate()
          }}
        >
          <PasswordField label={t('users.newPassword')} value={password} onChange={setPassword} error={error} />
          <p className="text-xs text-slate-500">{t('users.setPasswordHint')}</p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={close}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" loading={save.isPending}>
              {t('common.save')}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

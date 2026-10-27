import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, KeyRound, MailPlus, MessageCircle, Trash2, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { ConfirmDialog, Modal } from '../../components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { toApiError } from '../../services/apiClient'
import { memberService } from '../../services/organizations'
import type { Invitation, Member, Role } from '../../types/api'
import { formatDate, formatMobile, loginOf } from '../../utils/format'
import { DownloadMenu } from '../../components/DownloadMenu'
import { LoginShareCard, PasswordField } from '../../components/LoginDetails'

export function UsersPage() {
  const { t } = useTranslation()
  const { activeOrgId, can } = useOrg()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const canManage = can('members.manage')
  const [inviting, setInviting] = useState(false)
  const [adding, setAdding] = useState(false)
  const [passwordFor, setPasswordFor] = useState<Member | null>(null)
  const [removing, setRemoving] = useState<Member | null>(null)
  const members = useQuery({ queryKey: ['org', activeOrgId, 'members'], queryFn: () => memberService.list({}) })
  const roles = useQuery({ queryKey: ['org', activeOrgId, 'roles'], queryFn: memberService.roles })
  const invitations = useQuery({
    queryKey: ['org', activeOrgId, 'invitations'],
    queryFn: () => memberService.invitations({ status: 'pending' }),
    enabled: canManage,
  })
  const update = useMutation({
    mutationFn: ({ id, ...input }: { id: string; role_id?: string; status?: Member['status']; can_download?: boolean | null }) => memberService.update(id, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'members'] })
      notify(t('common.saved'))
    },
    onError,
  })
  const remove = useMutation({
    mutationFn: (id: string) => memberService.remove(id),
    onSuccess: async () => {
      setRemoving(null)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'members'] })
      notify(t('users.deleted'))
    },
    onError,
  })
  const revoke = useMutation({
    mutationFn: memberService.revokeInvitation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'invitations'] })
      notify(t('users.invitationRevoked'))
    },
    onError,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('users.title')}
        description={t('users.subtitle')}
        actions={
          <>
            <DownloadMenu path="/members/" params={{}} />
            {canManage && (
              <>
                <Button variant="secondary" icon={<MailPlus className="size-4" />} onClick={() => setInviting(true)}>
                  {t('users.invite')}
                </Button>
                <Button icon={<UserPlus className="size-4" />} onClick={() => setAdding(true)}>
                  {t('users.add')}
                </Button>
              </>
            )}
          </>
        }
      />
      <Card>
        {members.isLoading ? (
          <SkeletonRows />
        ) : members.isError ? (
          <ErrorState onRetry={() => void members.refetch()} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {members.data!.results.map((member) => {
              const self = member.user.id === user?.id
              return (
                <li key={member.id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {member.user.full_name} {self && <span className="text-xs text-slate-500">({t('users.you')})</span>}
                    </p>
                    <p className="truncate text-sm text-slate-500">
                      {[member.user.username && `${t('users.username')}: ${member.user.username}`, formatMobile(member.user.mobile), member.user.email].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  {member.status !== 'active' && <Badge tone="amber">{t(`status.${member.status}`)}</Badge>}
                  {canManage && !self ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        aria-label={t('users.role')}
                        value={member.role.id}
                        onChange={(e) => update.mutate({ id: member.id, role_id: e.target.value })}
                        className="h-9 rounded-lg border-0 py-0 text-sm ring-1 ring-slate-300"
                      >
                        {(roles.data ?? []).map((role) => (
                          <option key={role.id} value={role.id}>
                            {t(`roles.${role.code}`, role.name)}
                          </option>
                        ))}
                      </select>
                      <select
                        aria-label={t('download.access')}
                        title={t('download.access')}
                        value={member.can_download === null ? 'role' : member.can_download ? 'yes' : 'no'}
                        onChange={(e) => update.mutate({ id: member.id, can_download: { role: null, yes: true, no: false }[e.target.value as 'role' | 'yes' | 'no'] })}
                        className="h-9 rounded-lg border-0 py-0 text-sm ring-1 ring-slate-300"
                      >
                        <option value="role">
                          {t('download.roleDefault', {
                            value: (roles.data ?? []).find((role) => role.id === member.role.id)?.permissions['reports.export'] ? t('download.yes') : t('download.no'),
                          })}
                        </option>
                        <option value="yes">{t('download.allowed')}</option>
                        <option value="no">{t('download.notAllowed')}</option>
                      </select>
                      {member.can_reset_password && (
                        <Button variant="ghost" size="sm" icon={<KeyRound className="size-4" />} onClick={() => setPasswordFor(member)}>
                          {t('users.setPassword')}
                        </Button>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => update.mutate({ id: member.id, status: member.status === 'active' ? 'suspended' : 'active' })}
                      >
                        {member.status === 'active' ? t('users.suspend') : t('users.reactivate')}
                      </Button>
                      <Button variant="ghost" size="sm" icon={<Trash2 className="size-4" />} onClick={() => setRemoving(member)}>
                        {t('users.delete')}
                      </Button>
                    </div>
                  ) : (
                    <Badge tone="brand">{t(`roles.${member.role.code}`, member.role.name)}</Badge>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      {canManage && (
        <Card>
          <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('users.pendingInvitations')}</h2>
          {invitations.isLoading ? (
            <SkeletonRows rows={2} />
          ) : (invitations.data?.count ?? 0) === 0 ? (
            <EmptyState title={t('users.noInvitations')} message={t('users.noInvitationsMessage')} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {invitations.data!.results.map((invitation) => (
                <li key={invitation.id} className="flex flex-col gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center">
                  <div className="flex-1">
                    <p className="font-medium">{invitation.full_name || invitation.email || formatMobile(invitation.mobile)}</p>
                    <p className="text-slate-500">
                      {t(`roles.${invitation.role.code}`, invitation.role.name)} · {t('users.expires', { date: formatDate(invitation.expires_at) })}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" loading={revoke.isPending && revoke.variables === invitation.id} onClick={() => revoke.mutate(invitation.id)}>
                    {t('users.revoke')}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
      <InviteModal open={inviting} roles={roles.data ?? []} onClose={() => setInviting(false)} />
      <AddUserModal open={adding} roles={roles.data ?? []} onClose={() => setAdding(false)} />
      <SetPasswordModal member={passwordFor} onClose={() => setPasswordFor(null)} />
      <ConfirmDialog
        open={removing !== null}
        title={t('users.deleteTitle', { name: removing?.user.full_name ?? '' })}
        message={t('users.deleteMessage')}
        confirmLabel={t('users.delete')}
        danger
        loading={remove.isPending}
        onConfirm={() => removing && remove.mutate(removing.id)}
        onClose={() => setRemoving(null)}
      />
    </div>
  )
}

interface InviteValues {
  full_name: string
  email: string
  mobile: string
  role_id: string
}

function InviteModal({ open, roles, onClose }: { open: boolean; roles: Role[]; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [created, setCreated] = useState<Invitation | null>(null)
  const { register, handleSubmit, reset, setError, formState } = useForm<InviteValues>({ defaultValues: { full_name: '', email: '', mobile: '', role_id: '' } })
  const onError = useApiErrors(setError, ['full_name', 'email', 'mobile', 'role_id'])

  const close = () => {
    setCreated(null)
    reset()
    onClose()
  }
  const onSubmit = async (values: InviteValues) => {
    try {
      const invitation = await memberService.invite({
        full_name: values.full_name,
        email: values.email || undefined,
        mobile: values.mobile || undefined,
        role_id: values.role_id,
      })
      setCreated(invitation)
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'invitations'] })
    } catch (error) {
      onError(error)
    }
  }
  const shareText = created?.invite_url
    ? t('users.inviteMessage', { organization: detail?.organization.name, role: t(`roles.${created.role.code}`, created.role.name), link: created.invite_url })
    : ''

  return (
    <Modal open={open} title={t('users.invite')} onClose={close}>
      {created ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{t('users.inviteCreated')}</p>
          {created.email && created.email_sent === false && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{t('users.inviteEmailFailed')}</p>}
          <p className="break-all rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{created.invite_url}</p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              icon={<Copy className="size-4" />}
              onClick={async () => {
                await navigator.clipboard.writeText(created.invite_url!)
                notify(t('common.copied'))
              }}
            >
              {t('users.copyLink')}
            </Button>
            <a
              href={`https://wa.me/${(created.mobile ?? '').replace(/\D/g, '')}?text=${encodeURIComponent(shareText)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-medium text-white hover:bg-emerald-700"
            >
              <MessageCircle className="size-4" /> {t('users.shareWhatsApp')}
            </a>
          </div>
          <p className="text-xs text-slate-500">{t('users.inviteOnce')}</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <TextInput label={t('users.name')} {...register('full_name')} />
          <TextInput label={t('auth.email')} type="email" error={formState.errors.email?.message} {...register('email')} />
          <TextInput label={t('auth.mobile')} type="tel" inputMode="tel" error={formState.errors.mobile?.message} {...register('mobile')} />
          <p className="text-xs text-slate-500">{t('users.inviteHint')}</p>
          <SelectInput label={t('users.role')} required error={formState.errors.role_id && (formState.errors.role_id.message || t('validation.required'))} {...register('role_id', { required: true })}>
            <option value="">{t('users.chooseRole')}</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {t(`roles.${role.code}`, role.name)}
              </option>
            ))}
          </SelectInput>
          {formState.errors.root && <p className="text-sm text-red-600">{formState.errors.root.message}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={close}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" loading={formState.isSubmitting}>
              {t('users.sendInvite')}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

interface AddValues {
  full_name: string
  username: string
  email: string
  mobile: string
  password: string
  role_id: string
}

/** The admin types in the person's details and password; no invitation link is needed. */
function AddUserModal({ open, roles, onClose }: { open: boolean; roles: Role[]; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const queryClient = useQueryClient()
  const [added, setAdded] = useState<{ member: Member; password: string } | null>(null)
  const { register, handleSubmit, reset, setError, setValue, watch, formState } = useForm<AddValues>({
    defaultValues: { full_name: '', username: '', email: '', mobile: '', password: '', role_id: '' },
  })
  const onError = useApiErrors(setError, ['full_name', 'username', 'email', 'mobile', 'password', 'role_id'])
  register('password', { required: true })

  const close = () => {
    setAdded(null)
    reset()
    onClose()
  }
  const onSubmit = async (values: AddValues) => {
    try {
      const member = await memberService.add({
        full_name: values.full_name,
        username: values.username.trim() || undefined,
        email: values.email || undefined,
        mobile: values.mobile || undefined,
        password: values.password,
        role_id: values.role_id,
      })
      setAdded({ member, password: values.password })
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'members'] })
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'invitations'] })
    } catch (error) {
      onError(error)
    }
  }

  return (
    <Modal open={open} title={t('users.add')} onClose={close}>
      {added ? (
        <div className="space-y-4">
          {added.member.new_login === false ? (
            <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{t('users.addedExisting', { name: added.member.user.full_name })}</p>
          ) : (
            <>
              <p className="text-sm text-slate-600">{t('users.added', { name: added.member.user.full_name })}</p>
              <LoginShareCard
                name={added.member.user.full_name}
                organization={detail?.organization.name}
                identifier={loginOf(added.member.user)}
                mobile={added.member.user.mobile}
                password={added.password}
              />
            </>
          )}
          <div className="flex justify-end">
            <Button onClick={close}>{t('common.close')}</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <TextInput label={t('users.name')} required error={formState.errors.full_name && (formState.errors.full_name.message || t('validation.required'))} {...register('full_name', { required: true })} />
          <TextInput
            label={t('users.username')}
            autoCapitalize="none"
            autoComplete="off"
            spellCheck={false}
            hint={t('users.usernameHint')}
            error={formState.errors.username?.message}
            {...register('username')}
          />
          <TextInput label={t('auth.mobile')} type="tel" inputMode="tel" error={formState.errors.mobile?.message} {...register('mobile')} />
          <TextInput label={t('auth.email')} type="email" error={formState.errors.email?.message} {...register('email')} />
          <p className="text-xs text-slate-500">{t('users.addHint')}</p>
          <PasswordField
            value={watch('password')}
            onChange={(value) => setValue('password', value, { shouldValidate: formState.isSubmitted })}
            error={formState.errors.password && (formState.errors.password.message || t('validation.required'))}
          />
          <SelectInput label={t('users.role')} required error={formState.errors.role_id && (formState.errors.role_id.message || t('validation.required'))} {...register('role_id', { required: true })}>
            <option value="">{t('users.chooseRole')}</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {t(`roles.${role.code}`, role.name)}
              </option>
            ))}
          </SelectInput>
          {formState.errors.root && <p className="text-sm text-red-600">{formState.errors.root.message}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={close}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" loading={formState.isSubmitting}>
              {t('users.addButton')}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

function SetPasswordModal({ member, onClose }: { member: Member | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { detail } = useOrg()
  const [password, setPassword] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setFieldError] = useState<string | undefined>()
  const onError = useApiErrors()
  const save = useMutation({
    mutationFn: () => memberService.setPassword(member!.id, password),
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
  if (!member) return null
  return (
    <Modal open title={t('users.setPasswordFor', { name: member.user.full_name })} onClose={close}>
      {saved ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{t('users.passwordSet')}</p>
          <LoginShareCard
            name={member.user.full_name}
            organization={detail?.organization.name}
            identifier={loginOf(member.user)}
            mobile={member.user.mobile}
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

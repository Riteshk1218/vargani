import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, MailPlus, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { memberService } from '../../services/organizations'
import type { Invitation, Member, Role } from '../../types/api'
import { formatDate, formatMobile } from '../../utils/format'

export function UsersPage() {
  const { t } = useTranslation()
  const { activeOrgId, can } = useOrg()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const canManage = can('members.manage')
  const [inviting, setInviting] = useState(false)
  const members = useQuery({ queryKey: ['org', activeOrgId, 'members'], queryFn: () => memberService.list({}) })
  const roles = useQuery({ queryKey: ['org', activeOrgId, 'roles'], queryFn: memberService.roles })
  const invitations = useQuery({
    queryKey: ['org', activeOrgId, 'invitations'],
    queryFn: () => memberService.invitations({ status: 'pending' }),
    enabled: canManage,
  })
  const update = useMutation({
    mutationFn: ({ id, ...input }: { id: string; role_id?: string; status?: Member['status'] }) => memberService.update(id, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'members'] })
      notify(t('common.saved'))
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
          canManage && (
            <Button icon={<MailPlus className="size-4" />} onClick={() => setInviting(true)}>
              {t('users.invite')}
            </Button>
          )
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
                    <p className="truncate text-sm text-slate-500">{member.user.email ?? formatMobile(member.user.mobile)}</p>
                  </div>
                  {member.status !== 'active' && <Badge tone="amber">{t(`status.${member.status}`)}</Badge>}
                  {canManage && !self ? (
                    <div className="flex items-center gap-2">
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
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => update.mutate({ id: member.id, status: member.status === 'active' ? 'suspended' : 'active' })}
                      >
                        {member.status === 'active' ? t('users.suspend') : t('users.reactivate')}
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

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, HandCoins, Trash2, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { ConfirmDialog, Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows, Spinner } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { eventService } from '../../services/events'
import { peopleService } from '../../services/people'
import type { EventParticipant } from '../../types/api'
import { formatDate, formatMobile, formatMoney } from '../../utils/format'
import { EventMoneySetup } from './EventMoneySetup'
import { STATUS_TONE } from './EventsPage'

const PARTICIPATION_ROLES: EventParticipant['participation_role'][] = ['participant', 'volunteer', 'karyakarta', 'guest']

export function EventDetailPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const { activeOrgId, can, detail } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState(false)
  const [confirm, setConfirm] = useState<'close' | 'reopen' | null>(null)
  const event = useQuery({ queryKey: ['org', activeOrgId, 'events', 'detail', id], queryFn: () => eventService.get(id) })
  const participants = useQuery({
    queryKey: ['org', activeOrgId, 'events', id, 'participants', page],
    queryFn: () => eventService.participants(id, { page }),
    enabled: event.isSuccess,
  })
  const transition = useMutation({
    mutationFn: (action: 'close' | 'reopen') => eventService.transition(id, action),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'events'] })
      notify(t('common.saved'))
      setConfirm(null)
    },
    onError,
  })

  const navigate = useNavigate()
  const remove = useMutation({
    mutationFn: () => eventService.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('events.deleted'))
      navigate('/app/events')
    },
    onError,
  })

  if (event.isLoading) return <Spinner />
  if (event.isError) return <ErrorState message={t('errors.notFound')} />
  const e = event.data!
  const canManage = can('events.manage')

  return (
    <div>
      <Link to="/app/events" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="size-4" /> {t('events.title')}
      </Link>
      <PageHeader
        title={e.name}
        description={`${e.code} · ${e.financial_year_label}`}
        actions={
          <div className="flex gap-2">
            {can('payments.create') && e.status === 'active' && (
              <Link to={`/app/collect?event=${e.id}`}>
                <Button icon={<HandCoins className="size-4" />}>{t('collect.title')}</Button>
              </Link>
            )}
            {canManage &&
          (e.status === 'closed' ? (
            <Button variant="secondary" onClick={() => setConfirm('reopen')}>
              {t('events.reopen')}
            </Button>
          ) : e.status !== 'archived' ? (
            <Button variant="secondary" onClick={() => setConfirm('close')}>
              {t('events.close')}
            </Button>
          ) : null)}
            {can('records.admin_edit') && (
              <Button
                variant="ghost"
                icon={<Trash2 className="size-4" />}
                loading={remove.isPending}
                onClick={() => window.confirm(t('events.deleteConfirm', { name: e.name })) && remove.mutate()}
              >
                {t('common.delete')}
              </Button>
            )}
          </div>
        }
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="space-y-3 p-5 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">{t('common.status')}</span>
            <Badge tone={STATUS_TONE[e.status]}>{t(`status.${e.status}`)}</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">{t('events.dates')}</span>
            <span>
              {formatDate(e.start_date)} – {formatDate(e.end_date)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">{t('events.target')}</span>
            <span>{e.target_amount ? formatMoney(e.target_amount, detail?.organization.currency) : t('events.noTarget')}</span>
          </div>
          {e.description && <p className="whitespace-pre-line text-slate-700">{e.description}</p>}
          <div>
            <p className="mb-2 text-slate-500">{t('events.modules')}</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(e.modules)
                .filter(([, enabled]) => enabled)
                .map(([module]) => (
                  <Badge key={module} tone="brand">
                    {t(`events.module.${module}`)}
                  </Badge>
                ))}
            </div>
          </div>
        </Card>
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h2 className="font-semibold">{t('events.participants')}</h2>
            {canManage && (
              <Button size="sm" icon={<UserPlus className="size-4" />} onClick={() => setAdding(true)}>
                {t('events.addParticipant')}
              </Button>
            )}
          </div>
          {participants.isLoading ? (
            <SkeletonRows rows={3} />
          ) : participants.isError ? (
            <ErrorState onRetry={() => void participants.refetch()} />
          ) : participants.data!.count === 0 ? (
            <EmptyState title={t('events.noParticipants')} message={t('events.noParticipantsMessage')} />
          ) : (
            <>
              <ul className="divide-y divide-slate-100">
                {participants.data!.results.map((p) => (
                  <li key={p.id} className="flex items-center justify-between px-4 py-3 text-sm">
                    <div>
                      <p className="font-medium">{p.person_name}</p>
                      <p className="text-slate-500">{formatMobile(p.person_mobile)}</p>
                    </div>
                    <Badge>{t(`participation.${p.participation_role}`)}</Badge>
                  </li>
                ))}
              </ul>
              <Pagination page={page} pageSize={25} count={participants.data!.count} onChange={setPage} />
            </>
          )}
        </Card>
      </div>
      {can('contribution_types.view') && <EventMoneySetup eventId={id} />}
      <AddParticipantModal eventId={id} open={adding} onClose={() => setAdding(false)} />
      <ConfirmDialog
        open={confirm !== null}
        title={confirm === 'close' ? t('events.closeTitle') : t('events.reopenTitle')}
        message={confirm === 'close' ? t('events.closeMessage') : t('events.reopenMessage')}
        confirmLabel={confirm === 'close' ? t('events.close') : t('events.reopen')}
        loading={transition.isPending}
        onConfirm={() => confirm && transition.mutate(confirm)}
        onClose={() => setConfirm(null)}
      />
    </div>
  )
}

function AddParticipantModal({ eventId, open, onClose }: { eventId: string; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<EventParticipant['participation_role']>('participant')
  const people = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'picker', search],
    queryFn: () => peopleService.list({ search, page_size: 10 }),
    enabled: open,
  })
  const add = useMutation({
    mutationFn: (person: string) => eventService.addParticipant({ event: eventId, person, participation_role: role }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'events', eventId, 'participants'] })
      notify(t('events.participantAdded'))
    },
    onError,
  })
  return (
    <Modal open={open} title={t('events.addParticipant')} onClose={onClose}>
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <TextInput label={t('common.search')} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('people.searchPlaceholder')} />
          <SelectInput label={t('events.participationRole')} value={role} onChange={(e) => setRole(e.target.value as EventParticipant['participation_role'])}>
            {PARTICIPATION_ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`participation.${r}`)}
              </option>
            ))}
          </SelectInput>
        </div>
        {people.isLoading ? (
          <Spinner />
        ) : (people.data?.results.length ?? 0) === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">{t('people.noMatches')}</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
            {people.data!.results.map((person) => (
              <li key={person.id} className="flex items-center justify-between px-3 py-2 text-sm">
                <span>
                  <span className="font-medium">{person.full_name}</span>
                  <span className="block text-slate-500">{formatMobile(person.mobile)}</span>
                </span>
                <Button size="sm" variant="secondary" loading={add.isPending && add.variables === person.id} onClick={() => add.mutate(person.id)}>
                  {t('common.add')}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  )
}

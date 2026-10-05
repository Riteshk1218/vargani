import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, UserMinus, UserPlus, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { useDebounced } from '../../hooks/useDebounced'
import { collectorService } from '../../services/finance'
import { memberService } from '../../services/organizations'
import { peopleService } from '../../services/people'
import { formatMobile, formatMoney } from '../../utils/format'

const COLLECTING_ROLES = new Set(['collector', 'treasurer', 'org_admin'])

export function CollectorsPage() {
  const { t } = useTranslation()
  const { activeEvent } = useEvents()
  const { can, scope } = useOrg()
  if (!activeEvent) {
    return (
      <div>
        <PageHeader title={t('collectors.title')} />
        <Card>
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        </Card>
      </div>
    )
  }
  return (
    <div className="space-y-6">
      <PageHeader title={t('collectors.title')} description={`${activeEvent.name} · ${t('collectors.subtitle')}`} />
      {scope('collectors.view_performance') === 'all' && <Performance eventId={activeEvent.id} />}
      {can('collectors.manage') && <Assignments eventId={activeEvent.id} />}
    </div>
  )
}

function Performance({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const currency = detail?.organization.currency
  const rows = useQuery({ queryKey: ['org', activeOrgId, 'collectors', 'performance', eventId], queryFn: () => collectorService.performance(eventId) })
  return (
    <Card>
      <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">{t('collectors.performance')}</h2>
      {rows.isLoading ? (
        <SkeletonRows rows={3} />
      ) : rows.isError ? (
        <ErrorState onRetry={() => void rows.refetch()} />
      ) : rows.data!.length === 0 ? (
        <EmptyState title={t('collectors.noneYet')} message={t('collectors.noneYetMessage')} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">{t('collectors.name')}</th>
                <th className="px-4 py-2 text-right font-medium">{t('collectors.assigned')}</th>
                <th className="hidden px-4 py-2 text-right font-medium sm:table-cell">{t('mode.cash')}</th>
                <th className="hidden px-4 py-2 text-right font-medium sm:table-cell">{t('mode.upi')}</th>
                <th className="px-4 py-2 text-right font-medium">{t('common.total')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.data!.map((r) => (
                <tr key={r.membership}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{r.name}</p>
                    <p className="text-xs text-slate-500">{t('collectors.paymentsCount', { count: r.payments })}</p>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.assigned}</td>
                  <td className="hidden px-4 py-3 text-right tabular-nums sm:table-cell">{formatMoney(r.cash, currency)}</td>
                  <td className="hidden px-4 py-3 text-right tabular-nums sm:table-cell">{formatMoney(r.upi, currency)}</td>
                  <td className="px-4 py-3 text-right font-semibold tabular-nums">{formatMoney(r.total, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function Assignments({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const onError = useApiErrors()
  const [collector, setCollector] = useState('')
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState(false)
  const members = useQuery({ queryKey: ['org', activeOrgId, 'members', 'all'], queryFn: () => memberService.list({ page_size: 100 }) })
  const collectors = (members.data?.results ?? []).filter((m) => m.status === 'active' && COLLECTING_ROLES.has(m.role.code))
  const chosen = collector || collectors.find((m) => m.role.code === 'collector')?.id || collectors[0]?.id || ''
  const list = useQuery({
    queryKey: ['org', activeOrgId, 'collector-assignments', eventId, chosen, page],
    queryFn: () => collectorService.assignments({ event: eventId, collector: chosen, is_active: true, page }),
    enabled: Boolean(chosen),
  })
  const end = useMutation({
    mutationFn: (id: string) => collectorService.end(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'collector-assignments'] }),
    onError,
  })

  return (
    <Card>
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-semibold">{t('collectors.assignments')}</h2>
          <p className="text-xs text-slate-500">{t('collectors.assignmentsHelp')}</p>
        </div>
        <div className="flex items-end gap-2">
          <SelectInput label={t('collectors.collector')} value={chosen} onChange={(e) => (setCollector(e.target.value), setPage(1))}>
            {collectors.map((m) => (
              <option key={m.id} value={m.id}>
                {m.user.full_name} · {t(`roles.${m.role.code}`, { defaultValue: m.role.name })}
              </option>
            ))}
          </SelectInput>
          <Button icon={<UserPlus className="size-4" />} disabled={!chosen} onClick={() => setAdding(true)}>
            {t('collectors.assignPeople')}
          </Button>
        </div>
      </div>
      {!chosen ? (
        <EmptyState icon={<UsersRound className="size-6" />} title={t('collectors.noCollectors')} message={t('collectors.noCollectorsMessage')} />
      ) : list.isLoading ? (
        <SkeletonRows rows={3} />
      ) : list.isError ? (
        <ErrorState onRetry={() => void list.refetch()} />
      ) : list.data!.count === 0 ? (
        <EmptyState title={t('collectors.nobodyAssigned')} />
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {list.data!.results.map((a) => (
              <li key={a.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span>
                  <span className="font-medium">{a.person_name}</span>
                  <span className="block text-slate-500">{[formatMobile(a.person_mobile), a.person_area].filter(Boolean).join(' · ')}</span>
                </span>
                <Button variant="ghost" size="sm" aria-label={t('collectors.unassign')} loading={end.isPending && end.variables === a.id} onClick={() => end.mutate(a.id)}>
                  <UserMinus className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
          <Pagination page={page} pageSize={25} count={list.data!.count} onChange={setPage} />
        </>
      )}
      <AssignModal open={adding} eventId={eventId} collector={chosen} onClose={() => setAdding(false)} />
    </Card>
  )
}

function AssignModal({ open, eventId, collector, onClose }: { open: boolean; eventId: string; collector: string; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const debounced = useDebounced(search)
  const people = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'assign-picker', debounced],
    queryFn: () => peopleService.list({ search: debounced || undefined, page_size: 50 }),
    enabled: open,
  })
  const assign = useMutation({
    mutationFn: () => collectorService.assign(eventId, collector, [...selected]),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('collectors.assigned_done', { count: created.length }))
      setSelected(new Set())
      onClose()
    },
    onError,
  })
  const toggle = (id: string) =>
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  return (
    <Modal
      open={open}
      title={t('collectors.assignPeople')}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button disabled={selected.size === 0} loading={assign.isPending} onClick={() => assign.mutate()}>
            {t('collectors.assignCount', { count: selected.size })}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div className="relative">
          <TextInput label={t('common.search')} placeholder={t('people.searchPlaceholder')} value={search} onChange={(e) => setSearch(e.target.value)} />
          <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
        </div>
        <p className="text-xs text-slate-500">{t('collectors.moveNote')}</p>
        <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto rounded-lg ring-1 ring-slate-200">
          {(people.data?.results ?? []).map((p) => (
            <li key={p.id}>
              <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-slate-50">
                <input type="checkbox" className="size-4 rounded border-slate-300 text-brand-700" checked={selected.has(p.id)} onChange={() => toggle(p.id)} />
                <span>
                  <span className="font-medium">{p.full_name}</span>
                  <span className="block text-slate-500">{[formatMobile(p.mobile), p.area].filter(Boolean).join(' · ')}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  )
}

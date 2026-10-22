import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, KeyRound, Pencil, Search, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { ConfirmDialog } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { useDebounced } from '../../hooks/useDebounced'
import { peopleService } from '../../services/people'
import type { Person, PersonType } from '../../types/api'
import { formatMobile } from '../../utils/format'
import { LinkLoginModal } from './LinkLoginModal'
import { PERSON_TYPES, PersonFormModal } from './PersonFormModal'
import { DownloadMenu } from '../../components/DownloadMenu'

export function PeoplePage() {
  const { t } = useTranslation()
  const { activeOrgId, can } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [type, setType] = useState<PersonType | ''>('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Person | null>(null)
  const [archiving, setArchiving] = useState<Person | null>(null)
  const debouncedSearch = useDebounced(search)
  const creating = params.get('new') === '1'
  const canManage = can('people.manage')
  const canLink = canManage && can('members.view')
  const [linking, setLinking] = useState<Person | null>(null)

  const people = useQuery({
    queryKey: ['org', activeOrgId, 'people', 'list', debouncedSearch, type, page],
    queryFn: () => peopleService.list({ search: debouncedSearch || undefined, person_type: type || undefined, page }),
  })
  const archive = useMutation({
    mutationFn: (id: string) => peopleService.archive(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'people'] })
      notify(t('people.archived'))
      setArchiving(null)
    },
    onError,
  })
  const filtersActive = Boolean(debouncedSearch || type)

  return (
    <div>
      <PageHeader
        title={t('people.title')}
        description={t('people.subtitle')}
        actions={
          <>
            <DownloadMenu path="/people/" params={{ search: debouncedSearch, person_type: type }} />
            {canManage && (
              <Button icon={<UserPlus className="size-4" />} onClick={() => setParams({ new: '1' })}>
                {t('people.add')}
              </Button>
            )}
          </>
        }
      />
      <Card>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-[1fr_12rem]">
          <div className="relative">
            <TextInput
              label={t('common.search')}
              placeholder={t('people.searchPlaceholder')}
              value={search}
              onChange={(e) => (setSearch(e.target.value), setPage(1))}
            />
            <Search className="pointer-events-none absolute right-3 top-9 size-4 text-slate-400" aria-hidden />
          </div>
          <SelectInput label={t('people.type')} value={type} onChange={(e) => (setType(e.target.value as PersonType | ''), setPage(1))}>
            <option value="">{t('common.all')}</option>
            {PERSON_TYPES.map((value) => (
              <option key={value} value={value}>
                {t(`personType.${value}`)}
              </option>
            ))}
          </SelectInput>
        </div>
        {people.isLoading ? (
          <SkeletonRows />
        ) : people.isError ? (
          <ErrorState onRetry={() => void people.refetch()} />
        ) : people.data!.count === 0 ? (
          filtersActive ? (
            <EmptyState title={t('people.noMatches')} />
          ) : (
            <EmptyState
              icon={<UserPlus className="size-6" />}
              title={t('people.emptyTitle')}
              message={t('people.emptyMessage')}
              action={canManage && <Button onClick={() => setParams({ new: '1' })}>{t('people.add')}</Button>}
            />
          )
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-2 font-medium">{t('people.fullName')}</th>
                    <th className="hidden px-4 py-2 font-medium sm:table-cell">{t('people.mobile')}</th>
                    <th className="hidden px-4 py-2 font-medium md:table-cell">{t('people.area')}</th>
                    <th className="hidden px-4 py-2 font-medium lg:table-cell">{t('people.types')}</th>
                    {canManage && <th className="px-4 py-2" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {people.data!.results.map((person) => (
                    <tr key={person.id}>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">
                          {person.full_name}
                          {person.linked_user && (
                            <span className="ml-2 align-middle">
                              <Badge tone="green">{t('linkLogin.badge')}</Badge>
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-slate-500 sm:hidden">{formatMobile(person.mobile)}</p>
                      </td>
                      <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{formatMobile(person.mobile)}</td>
                      <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{[person.unit, person.building, person.area].filter(Boolean).join(', ')}</td>
                      <td className="hidden px-4 py-3 lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {person.person_types.map((pt) => (
                            <Badge key={pt}>{t(`personType.${pt}`)}</Badge>
                          ))}
                        </div>
                      </td>
                      {canManage && (
                        <td className="whitespace-nowrap px-4 py-3 text-right">
                          <Button variant="ghost" size="sm" aria-label={t('common.edit')} onClick={() => setEditing(person)}>
                            <Pencil className="size-4" />
                          </Button>
                          {canLink && (
                            <Button variant="ghost" size="sm" aria-label={t('linkLogin.title')} title={t('linkLogin.title')} onClick={() => setLinking(person)}>
                              <KeyRound className="size-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" aria-label={t('people.archive')} onClick={() => setArchiving(person)}>
                            <Archive className="size-4" />
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={25} count={people.data!.count} onChange={setPage} />
          </>
        )}
      </Card>
      <PersonFormModal
        open={creating || Boolean(editing)}
        person={editing}
        onClose={() => {
          setEditing(null)
          if (creating) setParams({})
        }}
      />
      <LinkLoginModal person={linking} onClose={() => setLinking(null)} />
      <ConfirmDialog
        open={Boolean(archiving)}
        title={t('people.archiveTitle')}
        message={t('people.archiveMessage', { name: archiving?.full_name })}
        confirmLabel={t('people.archive')}
        danger
        loading={archive.isPending}
        onConfirm={() => archiving && archive.mutate(archiving.id)}
        onClose={() => setArchiving(null)}
      />
    </div>
  )
}

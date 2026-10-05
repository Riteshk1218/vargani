import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { SelectInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { memberService } from '../../services/organizations'
import { peopleService } from '../../services/people'
import type { Person } from '../../types/api'

/** Connect a person record to a login, so that user sees this person's contributions in the member portal. */
export function LinkLoginModal({ person, onClose }: { person: Person | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [userId, setUserId] = useState('')
  const members = useQuery({
    queryKey: ['org', activeOrgId, 'members', 'all'],
    queryFn: () => memberService.list({ page_size: 100 }),
    enabled: person !== null,
  })
  const done = async (message: string) => {
    await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'people'] })
    notify(message)
    setUserId('')
    onClose()
  }
  const link = useMutation({ mutationFn: () => peopleService.linkUser(person!.id, userId), onSuccess: () => done(t('linkLogin.linked')), onError })
  const unlink = useMutation({ mutationFn: () => peopleService.unlinkUser(person!.id), onSuccess: () => done(t('linkLogin.unlinked')), onError })
  const active = members.data?.results.filter((m) => m.status === 'active') ?? []
  return (
    <Modal
      open={person !== null}
      title={t('linkLogin.title')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          {person?.linked_user ? (
            <Button variant="danger" loading={unlink.isPending} onClick={() => unlink.mutate()}>
              {t('linkLogin.unlink')}
            </Button>
          ) : (
            <Button loading={link.isPending} disabled={!userId} onClick={() => link.mutate()}>
              {t('linkLogin.link')}
            </Button>
          )}
        </>
      }
    >
      {person && (
        <div className="space-y-3 text-sm">
          <p className="text-slate-600">{t('linkLogin.help', { name: person.full_name })}</p>
          {person.linked_user ? (
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-800">{t('linkLogin.current', { name: person.linked_user_name })}</p>
          ) : (
            <>
              <SelectInput label={t('linkLogin.user')} value={userId} onChange={(e) => setUserId(e.target.value)}>
                <option value="">{t('common.choose')}</option>
                {active.map((m) => (
                  <option key={m.id} value={m.user.id}>
                    {m.user.full_name} · {m.user.mobile ?? m.user.email} · {m.role.name}
                  </option>
                ))}
              </SelectInput>
              <p className="text-xs text-slate-500">{t('linkLogin.autoHint')}</p>
            </>
          )}
        </div>
      )}
    </Modal>
  )
}

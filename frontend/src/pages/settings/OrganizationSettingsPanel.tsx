import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Checkbox } from '../../components/ui/Field'
import { ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { organizationService } from '../../services/organizations'
import type { OrganizationSettings } from '../../types/api'

const KEYS: (keyof OrganizationSettings)[] = ['allow_unassigned_collection', 'require_expense_approval', 'member_portal_enabled']

export function OrganizationSettingsPanel() {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const settings = useQuery({ queryKey: ['org', activeOrgId, 'settings'], queryFn: () => organizationService.settings(activeOrgId!) })
  const save = useMutation({
    mutationFn: (input: Partial<OrganizationSettings>) => organizationService.updateSettings(activeOrgId!, input),
    onSuccess: (data) => {
      queryClient.setQueryData(['org', activeOrgId, 'settings'], data)
      notify(t('common.saved'))
    },
    onError,
  })
  if (settings.isLoading) return <SkeletonRows rows={3} />
  if (settings.isError) return <ErrorState onRetry={() => void settings.refetch()} />
  return (
    <div className="space-y-5">
      {KEYS.map((key) => (
        <Checkbox
          key={key}
          label={t(`orgSettings.${key}`)}
          description={t(`orgSettings.${key}_help`)}
          checked={settings.data![key]}
          disabled={save.isPending}
          onChange={(e) => save.mutate({ [key]: e.target.checked })}
        />
      ))}
    </div>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { ThemePicker } from '../../components/theme/ThemePicker'
import { Checkbox } from '../../components/ui/Field'
import { ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { organizationService } from '../../services/organizations'
import type { OrganizationSettings } from '../../types/api'

const KEYS: Exclude<keyof OrganizationSettings, 'theme_color'>[] = ['allow_unassigned_collection', 'require_expense_approval', 'member_portal_enabled', 'auto_reminders']

function useOrgSettings() {
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
      void queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'me'] })
      notify(t('common.saved'))
    },
    onError,
  })
  return { settings, save }
}

/** The organization's app color: everyone in it sees this unless they chose their own. */
export function OrganizationThemePanel() {
  const { t } = useTranslation()
  const { settings, save } = useOrgSettings()
  if (settings.isLoading) return <SkeletonRows rows={2} />
  if (settings.isError) return <ErrorState onRetry={() => void settings.refetch()} />
  return (
    <div>
      <h2 className="font-semibold text-slate-900">{t('theme.orgColor')}</h2>
      <p className="mb-4 mt-1 text-sm text-slate-500">{t('theme.orgColorHelp')}</p>
      <ThemePicker value={settings.data!.theme_color ?? 'orange'} disabled={save.isPending} onChange={(color) => color && save.mutate({ theme_color: color })} />
    </div>
  )
}

export function OrganizationSettingsPanel() {
  const { t } = useTranslation()
  const { settings, save } = useOrgSettings()
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

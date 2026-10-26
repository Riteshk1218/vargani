import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Plus, RotateCcw, Save, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { Checkbox, TextInput } from '../../components/ui/Field'
import { ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { EMPTY_STUDIO, STUDIO_DEFAULT_LABELS } from '../../hooks/useFormStudio'
import { toApiError } from '../../services/apiClient'
import { organizationService } from '../../services/organizations'
import type { FormStudio, PaymentMode, StudioField, StudioLabelField } from '../../types/api'
import { MANUAL_MODES } from '../../utils/payments'
import { ContributionTypesCard } from '../events/EventMoneySetup'

const LABEL_FIELDS = Object.keys(STUDIO_DEFAULT_LABELS) as StudioLabelField[]

/** Admin studio: an Organization Admin changes the Collect form (names and dropdowns) without a new app. */
export function AdminStudioPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const { activeEvent } = useEvents()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const saved = useQuery({ queryKey: ['org', activeOrgId, 'form-studio'], queryFn: () => organizationService.formStudio(activeOrgId!) })
  const [draft, setDraft] = useState<FormStudio>(EMPTY_STUDIO)
  const [errors, setErrors] = useState<Record<string, string>>({})
  useEffect(() => {
    if (saved.data) setDraft(saved.data)
  }, [saved.data])

  const save = useMutation({
    mutationFn: (input: FormStudio) => organizationService.saveFormStudio(activeOrgId!, input),
    onSuccess: (data) => {
      queryClient.setQueryData(['org', activeOrgId, 'form-studio'], data)
      void queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'me'] })
      setErrors({})
      notify(t('studio.saved'))
    },
    onError: (error) => {
      const apiError = toApiError(error)
      setErrors(Object.fromEntries(Object.entries(apiError.details).map(([key, messages]) => [key, messages[0]])))
      notify(apiError.message || t('errors.generic'), 'error')
    },
  })

  if (saved.isLoading) return <SkeletonRows rows={6} />
  if (saved.isError) return <ErrorState onRetry={() => void saved.refetch()} />

  const changed = JSON.stringify(draft) !== JSON.stringify(saved.data)
  const setLabel = (field: StudioLabelField, value: string) => setDraft((d) => ({ ...d, labels: { ...d.labels, [field]: value } }))
  const setMode = (mode: PaymentMode, patch: Partial<{ label: string; hidden: boolean }>) =>
    setDraft((d) => ({ ...d, modes: { ...d.modes, [mode]: { label: '', hidden: false, ...d.modes[mode], ...patch } } }))
  const setFields = (update: (fields: StudioField[]) => StudioField[]) => setDraft((d) => ({ ...d, custom_fields: update(d.custom_fields) }))
  const updateField = (index: number, patch: Partial<StudioField>) => setFields((fs) => fs.map((f, i) => (i === index ? { ...f, ...patch } : f)))
  const moveField = (index: number, by: number) =>
    setFields((fs) => {
      const next = [...fs]
      const [field] = next.splice(index, 1)
      next.splice(index + by, 0, field)
      return next
    })

  return (
    <div className="mx-auto max-w-3xl pb-24">
      <PageHeader title={t('studio.title')} description={t('studio.subtitle', { name: detail?.organization.name })} />
      <div className="space-y-4">
        <section aria-labelledby="studio-types">
          <h2 id="studio-types" className="mb-1 font-semibold">
            {t('studio.typesTitle')}
          </h2>
          <p className="mb-2 text-sm text-slate-500">{activeEvent ? t('studio.typesHelp', { event: activeEvent.name }) : t('studio.typesNoEvent')}</p>
          {activeEvent && <ContributionTypesCard eventId={activeEvent.id} />}
        </section>

        <Card className="p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">{t('studio.fieldsTitle')}</h2>
              <p className="text-sm text-slate-500">{t('studio.fieldsHelp')}</p>
            </div>
            <Button
              size="sm"
              icon={<Plus className="size-4" />}
              disabled={draft.custom_fields.length >= 10}
              onClick={() => setFields((fs) => [...fs, { label: '', options: [''], required: false, active: true }])}
            >
              {t('studio.addField')}
            </Button>
          </div>
          {draft.custom_fields.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{t('studio.noFields')}</p>
          ) : (
            <ul className="space-y-3">
              {draft.custom_fields.map((field, index) => (
                <li key={field.key ?? `new-${index}`} className="rounded-lg p-3 ring-1 ring-slate-200" data-testid="studio-field">
                  <div className="flex items-start gap-2">
                    <TextInput
                      className="flex-1"
                      label={t('studio.fieldName')}
                      placeholder={t('studio.fieldNamePlaceholder')}
                      required
                      maxLength={60}
                      value={field.label}
                      error={errors[`custom_fields.${index}.label`]}
                      onChange={(e) => updateField(index, { label: e.target.value })}
                    />
                    <div className="mt-6 flex">
                      <Button variant="ghost" size="sm" aria-label={t('studio.moveUp')} disabled={index === 0} onClick={() => moveField(index, -1)}>
                        <ArrowUp className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={t('studio.moveDown')}
                        disabled={index === draft.custom_fields.length - 1}
                        onClick={() => moveField(index, 1)}
                      >
                        <ArrowDown className="size-4" />
                      </Button>
                    </div>
                  </div>
                  <p className="mb-1 mt-3 text-sm font-medium text-slate-700">{t('studio.options')}</p>
                  <ul className="space-y-2">
                    {field.options.map((option, o) => (
                      <li key={o} className="flex items-center gap-2">
                        <span className="w-6 text-right text-xs text-slate-400">{o + 1}.</span>
                        <input
                          aria-label={t('studio.optionN', { n: o + 1 })}
                          className="block w-full rounded-lg border-0 px-3 py-1.5 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-brand-600"
                          maxLength={60}
                          value={option}
                          placeholder={t('studio.optionPlaceholder')}
                          onChange={(e) => updateField(index, { options: field.options.map((v, i) => (i === o ? e.target.value : v)) })}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={t('studio.removeOption')}
                          disabled={field.options.length === 1}
                          onClick={() => updateField(index, { options: field.options.filter((_, i) => i !== o) })}
                        >
                          <X className="size-4" />
                        </Button>
                      </li>
                    ))}
                  </ul>
                  {errors[`custom_fields.${index}.options`] && <p className="mt-1 text-sm text-red-600">{errors[`custom_fields.${index}.options`]}</p>}
                  <Button
                    className="mt-2"
                    variant="secondary"
                    size="sm"
                    icon={<Plus className="size-4" />}
                    disabled={field.options.length >= 50}
                    onClick={() => updateField(index, { options: [...field.options, ''] })}
                  >
                    {t('studio.addOption')}
                  </Button>
                  <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 border-t border-slate-100 pt-3">
                    <Checkbox label={t('studio.required')} checked={field.required} onChange={(e) => updateField(index, { required: e.target.checked })} />
                    <Checkbox
                      label={t('studio.showOnCollect')}
                      description={field.key ? undefined : t('studio.newField')}
                      checked={field.active}
                      onChange={(e) => updateField(index, { active: e.target.checked })}
                    />
                    {!field.active && <Badge>{t('studio.hidden')}</Badge>}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500">{t('studio.fieldsNote')}</p>
        </Card>

        <Card className="p-4">
          <h2 className="font-semibold">{t('studio.modesTitle')}</h2>
          <p className="mb-3 text-sm text-slate-500">{t('studio.modesHelp')}</p>
          {errors.modes && <p className="mb-2 text-sm text-red-600">{errors.modes}</p>}
          <ul className="divide-y divide-slate-100">
            {MANUAL_MODES.map((mode) => {
              const value = draft.modes[mode]
              return (
                <li key={mode} className="grid items-center gap-2 py-2 sm:grid-cols-[10rem_1fr_auto]">
                  <span className="text-sm font-medium">{t(`mode.${mode}`)}</span>
                  <input
                    aria-label={t('studio.renameMode', { mode: t(`mode.${mode}`) })}
                    className="block w-full rounded-lg border-0 px-3 py-1.5 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-brand-600"
                    maxLength={60}
                    placeholder={t(`mode.${mode}`)}
                    value={value?.label ?? ''}
                    onChange={(e) => setMode(mode, { label: e.target.value })}
                  />
                  <Checkbox label={t('studio.show')} checked={!value?.hidden} onChange={(e) => setMode(mode, { hidden: !e.target.checked })} />
                </li>
              )
            })}
          </ul>
        </Card>

        <Card className="p-4">
          <h2 className="font-semibold">{t('studio.labelsTitle')}</h2>
          <p className="mb-3 text-sm text-slate-500">{t('studio.labelsHelp')}</p>
          <ul className="divide-y divide-slate-100">
            {LABEL_FIELDS.map((field) => (
              <li key={field} className="grid items-center gap-2 py-2 sm:grid-cols-[12rem_1fr]">
                <span className="text-sm font-medium">{t(STUDIO_DEFAULT_LABELS[field])}</span>
                <div>
                  <input
                    aria-label={t('studio.renameField', { field: t(STUDIO_DEFAULT_LABELS[field]) })}
                    className="block w-full rounded-lg border-0 px-3 py-1.5 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-brand-600"
                    maxLength={60}
                    placeholder={t('studio.keepStandard')}
                    value={draft.labels[field] ?? ''}
                    onChange={(e) => setLabel(field, e.target.value)}
                  />
                  {errors[`labels.${field}`] && <p className="mt-1 text-sm text-red-600">{errors[`labels.${field}`]}</p>}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-200 bg-white/95 p-3 backdrop-blur lg:left-64">
        <div className="mx-auto flex max-w-3xl items-center justify-end gap-2">
          {changed && <span className="mr-auto text-sm text-amber-700">{t('studio.unsaved')}</span>}
          <Button variant="secondary" icon={<RotateCcw className="size-4" />} disabled={!changed || save.isPending} onClick={() => saved.data && setDraft(saved.data)}>
            {t('studio.undo')}
          </Button>
          <Button icon={<Save className="size-4" />} disabled={!changed} loading={save.isPending} onClick={() => save.mutate(draft)}>
            {t('studio.save')}
          </Button>
        </div>
      </div>
    </div>
  )
}

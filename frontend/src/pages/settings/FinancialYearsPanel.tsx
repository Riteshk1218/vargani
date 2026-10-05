import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Card'
import { TextInput } from '../../components/ui/Field'
import { ConfirmDialog, Modal } from '../../components/ui/Modal'
import { ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { financialYearService } from '../../services/organizations'
import type { FinancialYear } from '../../types/api'
import { formatDate, suggestFinancialYear } from '../../utils/format'

export function FinancialYearsPanel() {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [creating, setCreating] = useState(false)
  const [closing, setClosing] = useState<FinancialYear | null>(null)
  const years = useQuery({ queryKey: ['org', activeOrgId, 'financial-years'], queryFn: financialYearService.list })
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
  }
  const setCurrent = useMutation({ mutationFn: financialYearService.setCurrent, onSuccess: async () => (await refresh(), notify(t('common.saved'))), onError })
  const close = useMutation({
    mutationFn: financialYearService.close,
    onSuccess: async () => {
      await refresh()
      setClosing(null)
      notify(t('common.saved'))
    },
    onError,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">{t('financialYears.help')}</p>
        <Button size="sm" onClick={() => setCreating(true)}>
          {t('financialYears.add')}
        </Button>
      </div>
      {years.isLoading ? (
        <SkeletonRows rows={2} />
      ) : years.isError ? (
        <ErrorState onRetry={() => void years.refetch()} />
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
          {years.data!.results.map((year) => (
            <li key={year.id} className="flex flex-col gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center">
              <div className="flex-1">
                <p className="flex items-center gap-2 font-medium">
                  {year.label}
                  {year.is_current && <Badge tone="green">{t('financialYears.current')}</Badge>}
                  {year.status === 'closed' && <Badge>{t('status.closed')}</Badge>}
                </p>
                <p className="text-slate-500">
                  {formatDate(year.start_date)} – {formatDate(year.end_date)}
                </p>
              </div>
              {year.status === 'open' && (
                <div className="flex gap-2">
                  {!year.is_current && (
                    <Button variant="secondary" size="sm" loading={setCurrent.isPending && setCurrent.variables === year.id} onClick={() => setCurrent.mutate(year.id)}>
                      {t('financialYears.makeCurrent')}
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => setClosing(year)}>
                    {t('financialYears.close')}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <CreateYearModal open={creating} onClose={() => setCreating(false)} onCreated={refresh} />
      <ConfirmDialog
        open={Boolean(closing)}
        title={t('financialYears.closeTitle', { label: closing?.label })}
        message={t('financialYears.closeMessage')}
        confirmLabel={t('financialYears.close')}
        danger
        loading={close.isPending}
        onConfirm={() => closing && close.mutate(closing.id)}
        onClose={() => setClosing(null)}
      />
    </div>
  )
}

function CreateYearModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => Promise<void> }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const next = suggestFinancialYear(new Date(new Date().getFullYear() + 1, 5, 1))
  const { register, handleSubmit, setError, formState, reset } = useForm({ defaultValues: next })
  const onError = useApiErrors(setError, ['label', 'start_date', 'end_date'])
  const onSubmit = async (values: typeof next) => {
    try {
      await financialYearService.create(values)
      await onCreated()
      notify(t('financialYears.created'))
      reset(next)
      onClose()
    } catch (error) {
      onError(error)
    }
  }
  return (
    <Modal
      open={open}
      title={t('financialYears.add')}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="fy-form" loading={formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <form id="fy-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <TextInput label={t('financialYears.label')} required error={formState.errors.label?.message} {...register('label', { required: true })} />
        <div className="grid grid-cols-2 gap-3">
          <TextInput label={t('financialYears.start')} type="date" required error={formState.errors.start_date?.message} {...register('start_date', { required: true })} />
          <TextInput label={t('financialYears.end')} type="date" required error={formState.errors.end_date?.message} {...register('end_date', { required: true })} />
        </div>
      </form>
    </Modal>
  )
}

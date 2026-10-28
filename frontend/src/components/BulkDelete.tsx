import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useOrg } from '../context/OrgContext'
import { useApiErrors } from '../hooks/useApiErrors'
import { api } from '../services/apiClient'
import { cn } from '../utils/cn'
import { Button } from './ui/Button'
import { ConfirmDialog } from './ui/Modal'
import { useToast } from './ui/Toast'

/** Only the Organization Admin (and the platform admin) may delete records. */
export const DELETE_PERMISSION = 'records.admin_edit'

interface BulkDeleteResult {
  deleted: number
  failed: { id: string; message: string }[]
}

/**
 * Rows ticked in a list, kept across pages so someone can pick 10 entries from two pages and delete them together.
 * `resetKey` (e.g. the filters) clears the choice when the list changes underneath it.
 */
export function useRowSelection(resetKey?: unknown) {
  const key = JSON.stringify(resetKey ?? null)
  const [state, setState] = useState<{ key: string; ids: Set<string> }>({ key, ids: new Set() })
  const selected = state.key === key ? state.ids : new Set<string>()
  const setSelected = (update: (current: Set<string>) => Set<string>) => setState((s) => ({ key, ids: update(s.key === key ? s.ids : new Set()) }))
  return {
    selected,
    count: selected.size,
    has: (id: string) => selected.has(id),
    toggle: (id: string) =>
      setSelected((current) => {
        const next = new Set(current)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        return next
      }),
    /** Ticks every row on this page, or unticks them when all already are. */
    toggleAll: (ids: string[]) =>
      setSelected((current) => {
        const next = new Set(current)
        const all = ids.length > 0 && ids.every((id) => next.has(id))
        for (const id of ids) {
          if (all) next.delete(id)
          else next.add(id)
        }
        return next
      }),
    clear: () => setSelected(() => new Set()),
  }
}

export type RowSelection = ReturnType<typeof useRowSelection>

/** A row's tick box. Clicking it never opens the row. */
export function SelectBox({ checked, indeterminate = false, onChange, label, className }: { checked: boolean; indeterminate?: boolean; onChange: () => void; label: string; className?: string }) {
  return (
    <input
      type="checkbox"
      aria-label={label}
      title={label}
      checked={checked}
      ref={(el) => {
        if (el) el.indeterminate = indeterminate && !checked
      }}
      onChange={onChange}
      onClick={(e) => e.stopPropagation()}
      className={cn('size-4 shrink-0 cursor-pointer rounded border-slate-300 text-brand-700 focus:ring-brand-600', className)}
    />
  )
}

/** The tick box of one row, as a table cell. */
export function SelectCell({ selection, id }: { selection: RowSelection; id: string }) {
  const { t } = useTranslation()
  return (
    <td className="w-10 px-4 py-3" onClick={(e) => e.stopPropagation()}>
      <SelectBox checked={selection.has(id)} onChange={() => selection.toggle(id)} label={t('bulk.select')} />
    </td>
  )
}

/** The "select all on this page" tick box, as a table header cell. */
export function SelectAllHeader({ selection, ids }: { selection: RowSelection; ids: string[] }) {
  const { t } = useTranslation()
  const all = ids.length > 0 && ids.every((id) => selection.has(id))
  return (
    <th className="w-10 px-4 py-2">
      <SelectBox checked={all} indeterminate={ids.some((id) => selection.has(id))} onChange={() => selection.toggleAll(ids)} label={t('bulk.selectAll')} />
    </th>
  )
}

/**
 * "Select all" for the page, how many rows are ticked, and a delete button that asks first, then sends them to
 * `<path>bulk-delete/`. Each record is deleted as it would be on its own, and the audit log keeps a copy.
 */
export function BulkDeleteBar({
  selection,
  ids,
  path,
  invalidate,
  showSelectAll = true,
  message,
}: {
  selection: RowSelection
  /** The rows on this page, for "select all". */
  ids: string[]
  /** List endpoint, e.g. "/payments/". */
  path: string
  /** Query keys (under the active organization) to refresh afterwards, e.g. [['payments'], ['dashboard']]. */
  invalidate: string[][]
  /** Set false when the table header already has a select-all box. */
  showSelectAll?: boolean
  /** What deleting these records does, shown in the confirmation. */
  message?: string
}) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [confirming, setConfirming] = useState(false)
  const remove = useMutation({
    mutationFn: (chosen: string[]) => api.post<BulkDeleteResult>(`${path}bulk-delete/`, { ids: chosen }).then((r) => r.data),
    onSuccess: async (result) => {
      setConfirming(false)
      selection.clear()
      await Promise.all(invalidate.map((key) => queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, ...key] })))
      if (result.deleted) notify(t('bulk.deleted', { count: result.deleted }))
      if (result.failed.length) notify(t('bulk.failed', { count: result.failed.length, reason: result.failed[0].message }), 'error')
    },
    onError,
  })
  if (ids.length === 0 && selection.count === 0) return null
  const all = ids.length > 0 && ids.every((id) => selection.has(id))
  return (
    <div className={cn('flex min-h-12 flex-wrap items-center gap-3 border-b border-slate-200 px-4 py-2 text-sm', selection.count > 0 && 'bg-red-50/60')}>
      {showSelectAll && (
        <label className="flex cursor-pointer items-center gap-2 text-slate-600">
          <SelectBox checked={all} indeterminate={ids.some((id) => selection.has(id))} onChange={() => selection.toggleAll(ids)} label={t('bulk.selectAll')} />
          {t('bulk.selectAll')}
        </label>
      )}
      {selection.count > 0 && (
        <>
          <span className="font-medium text-slate-800">{t('bulk.selected', { count: selection.count })}</span>
          <div className="ml-auto flex gap-2">
            <Button size="sm" variant="ghost" icon={<X className="size-4" />} onClick={selection.clear}>
              {t('bulk.clear')}
            </Button>
            <Button size="sm" variant="danger" icon={<Trash2 className="size-4" />} onClick={() => setConfirming(true)} data-testid="bulk-delete">
              {t('bulk.delete', { count: selection.count })}
            </Button>
          </div>
        </>
      )}
      <ConfirmDialog
        open={confirming}
        title={t('bulk.confirmTitle', { count: selection.count })}
        message={message ?? t('bulk.confirmMessage')}
        confirmLabel={t('bulk.delete', { count: selection.count })}
        danger
        loading={remove.isPending}
        onConfirm={() => remove.mutate([...selection.selected])}
        onClose={() => setConfirming(false)}
      />
    </div>
  )
}

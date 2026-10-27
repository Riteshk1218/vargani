import { ArrowDownWideNarrow, ArrowUpNarrowWide, CalendarDays, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { Button } from './ui/Button'
import { SelectInput, TextInput } from './ui/Field'
import { formatStamp } from '../utils/format'

/** Today as YYYY-MM-DD in the browser's own calendar. */
export function todayIso(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export interface SortOption {
  /** API ordering field, without the leading "-". */
  field: string
  label: string
}

/**
 * Date range and sort order of a list, kept in the address (?date_from=&date_to=&sort=-paid_at) so a dashboard
 * card can open the list already filtered, and Back keeps the choice.
 */
export function useListTools(defaultSort: string, onChange?: () => void) {
  const [params, setParams] = useSearchParams()
  const dateFrom = params.get('date_from') ?? ''
  const dateTo = params.get('date_to') ?? ''
  const ordering = params.get('sort') || defaultSort
  const update = (values: Record<string, string>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(values)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    setParams(next, { replace: true })
    onChange?.()
  }
  return {
    dateFrom,
    dateTo,
    ordering,
    /** Ready to spread into a list request. */
    query: { date_from: dateFrom || undefined, date_to: dateTo || undefined, ordering },
    filtered: Boolean(dateFrom || dateTo),
    setDates: (from: string, to: string) => update({ date_from: from, date_to: to }),
    setOrdering: (value: string) => update({ sort: value === defaultSort ? '' : value }),
  }
}

export type ListToolsState = ReturnType<typeof useListTools>

/** From / To dates, a Today shortcut, the field to sort by and ascending / descending. */
export function ListTools({ tools, sortOptions = [], dateLabel, className = 'border-b border-slate-200 p-4' }: { tools: ListToolsState; sortOptions?: SortOption[]; dateLabel?: string; className?: string }) {
  const { t } = useTranslation()
  const descending = tools.ordering.startsWith('-')
  const field = descending ? tools.ordering.slice(1) : tools.ordering
  const today = todayIso()
  return (
    <div className={`grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end ${className}`}>
      <TextInput
        label={dateLabel ? `${dateLabel} · ${t('list.from')}` : t('list.from')}
        type="date"
        value={tools.dateFrom}
        max={tools.dateTo || undefined}
        onChange={(e) => tools.setDates(e.target.value, tools.dateTo)}
        className="sm:w-40"
      />
      <TextInput label={t('list.to')} type="date" value={tools.dateTo} min={tools.dateFrom || undefined} onChange={(e) => tools.setDates(tools.dateFrom, e.target.value)} className="sm:w-40" />
      <div className="col-span-2 flex gap-2 sm:col-span-1">
        <Button variant={tools.dateFrom === today && tools.dateTo === today ? 'primary' : 'secondary'} icon={<CalendarDays className="size-4" />} onClick={() => tools.setDates(today, today)}>
          {t('list.today')}
        </Button>
        {tools.filtered && (
          <Button variant="ghost" icon={<X className="size-4" />} onClick={() => tools.setDates('', '')}>
            {t('list.allDates')}
          </Button>
        )}
      </div>
      {sortOptions.length > 0 && (
      <div className="col-span-2 flex items-end gap-2 sm:col-span-1 sm:ml-auto">
        <SelectInput label={t('list.sortBy')} value={field} onChange={(e) => tools.setOrdering(`${descending ? '-' : ''}${e.target.value}`)} className="min-w-0 flex-1 sm:w-44">
          {sortOptions.map((o) => (
            <option key={o.field} value={o.field}>
              {o.label}
            </option>
          ))}
        </SelectInput>
        <Button
          variant="secondary"
          aria-label={descending ? t('list.descending') : t('list.ascending')}
          title={descending ? t('list.descending') : t('list.ascending')}
          icon={descending ? <ArrowDownWideNarrow className="size-4" /> : <ArrowUpNarrowWide className="size-4" />}
          onClick={() => tools.setOrdering(descending ? field : `-${field}`)}
          data-testid="sort-direction"
        >
          {descending ? t('list.descendingShort') : t('list.ascendingShort')}
        </Button>
      </div>
      )}
    </div>
  )
}

/** "Created 27 Oct 2026, 10:30 am · Ritesh" under a row. */
export function CreatedMeta({ at, by, className = 'text-xs text-slate-500' }: { at?: string | null; by?: string | null; className?: string }) {
  const { t } = useTranslation()
  if (!at) return null
  return (
    <p className={className}>
      {t('list.created', { date: formatStamp(at) })}
      {by && ` · ${t('list.by', { name: by })}`}
    </p>
  )
}

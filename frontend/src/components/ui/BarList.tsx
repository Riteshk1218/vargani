import { formatMoney } from '../../utils/format'

/** Horizontal bars for money breakdowns. Values are decimal strings from the API. */
export function BarList({ items, currency, emptyLabel }: { items: { label: string; value: string }[]; currency?: string; emptyLabel: string }) {
  if (items.length === 0) return <p className="py-4 text-center text-sm text-slate-500">{emptyLabel}</p>
  const max = Math.max(...items.map((item) => Number(item.value)), 1)
  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item.label} className="text-sm">
          <div className="mb-1 flex justify-between gap-2">
            <span className="truncate text-slate-700">{item.label}</span>
            <span className="shrink-0 font-medium tabular-nums">{formatMoney(item.value, currency)}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div className="h-2 rounded-full bg-brand-600" style={{ width: `${Math.max(2, (Number(item.value) / max) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

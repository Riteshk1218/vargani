import { useTranslation } from 'react-i18next'
import type { Receipt } from '../../types/api'
import { formatMobile } from '../../utils/format'

/** The printable receipt. Everything shown comes from the snapshot taken when the receipt was issued. */
export function ReceiptView({ receipt }: { receipt: Pick<Receipt, 'language' | 'snapshot' | 'status' | 'logo_url' | 'receipt_number'> }) {
  const { i18n } = useTranslation()
  const lang = receipt.language || 'en'
  const t = i18n.getFixedT(lang)
  const s = receipt.snapshot
  const balanceLines = s.balance_lines ?? []
  const locale = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' }[lang] ?? 'en-IN'
  const money = (value: string) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: s.currency || 'INR' }).format(Number(value))
  // "08-Oct-2026, 10:35 PM" in the organization's time zone, whatever the viewer's computer is set to.
  const stamp = (value: string) => {
    const zone = s.timezone || 'Asia/Kolkata'
    const parts = (options: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(locale, { timeZone: zone, ...options }).format(new Date(value))
    const time = new Intl.DateTimeFormat('en-IN', { timeZone: zone, hour: '2-digit', minute: '2-digit', hour12: true }).format(new Date(value)).toUpperCase()
    return `${parts({ day: '2-digit' })}-${parts({ month: 'short' })}-${parts({ year: 'numeric' })}, ${time}`
  }
  const month = (value: string) => new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(new Date(`${value}T00:00:00`))

  return (
    <article className="receipt relative mx-auto max-w-2xl bg-white p-6 text-slate-900 sm:p-8" lang={lang}>
      {receipt.status === 'void' && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden>
          <span className="-rotate-12 rounded-lg border-4 border-red-600/60 px-6 py-2 text-5xl font-bold text-red-600/60">{t('receipts.void')}</span>
        </div>
      )}
      <header className="flex items-start gap-4 border-b-2 border-brand-700 pb-4">
        {receipt.logo_url && <img src={receipt.logo_url} alt="" className="size-16 rounded-lg object-contain" />}
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-bold leading-tight">{s.organization.name}</h1>
          {s.organization.address && <p className="text-sm text-slate-600">{s.organization.address}</p>}
          <p className="text-sm text-slate-600">
            {[formatMobile(s.organization.phone), s.organization.email].filter(Boolean).join(' · ')}
          </p>
          {s.organization.registration_number && (
            <p className="text-xs text-slate-500">
              {s.organization.registration_type || t('receipts.registration')}: {s.organization.registration_number}
            </p>
          )}
        </div>
      </header>

      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold uppercase tracking-wide text-brand-800">{t('receipts.heading')}</h2>
        <p className="text-sm">
          <span className="text-slate-500">{t('receipts.number')}: </span>
          <span className="font-mono font-semibold" data-testid="receipt-number">
            {receipt.receipt_number}
          </span>
        </p>
      </div>
      <dl className="mt-4 grid gap-1 text-sm">
        <div className="flex gap-2">
          <dt className="w-36 shrink-0 text-slate-500">{t('finance.event')}</dt>
          <dd>{s.event.name}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-36 shrink-0 text-slate-500">{t('finance.financialYear')}</dt>
          <dd>{s.financial_year}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-36 shrink-0 text-slate-500">{t('payments.dateTime')}</dt>
          <dd data-testid="receipt-stamp">{stamp(s.paid_at)}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-36 shrink-0 text-slate-500">{t('receipts.receivedFrom')}</dt>
          <dd className="font-semibold">{s.person.anonymous ? t('collect.anonymousName') : s.person.name}</dd>
        </div>
        {s.person.mobile && (
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-slate-500">{t('people.mobile')}</dt>
            <dd>{formatMobile(s.person.mobile)}</dd>
          </div>
        )}
        {s.person.address && (
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-slate-500">{t('people.address')}</dt>
            <dd>{s.person.address}</dd>
          </div>
        )}
      </dl>

      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="border-y border-slate-300 text-left">
            <th className="py-2 font-medium">{t('receipts.for')}</th>
            <th className="py-2 text-right font-medium">{t('common.amount')}</th>
          </tr>
        </thead>
        <tbody>
          {s.lines.map((line, index) => (
            <tr key={index} className="border-b border-slate-100">
              <td className="py-2">
                {line.contribution_type}
                {line.period_month && <span className="text-slate-600"> · {month(line.period_month)}</span>}
                {line.towards_balance && <span className="text-xs text-slate-500"> ({t('receipts.towardsBalance')})</span>}
                {line.fund && <span className="block text-xs text-slate-500">{line.fund}</span>}
              </td>
              <td className="py-2 text-right tabular-nums">{money(line.amount)}</td>
            </tr>
          ))}
          {s.lines.length === 0 && (
            <tr className="border-b border-slate-100">
              <td className="py-2 text-slate-500">{t('receipts.nothingReceived')}</td>
              <td className="py-2 text-right tabular-nums">{money('0')}</td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-800">
            <td className="py-2 font-semibold">{balanceLines.length ? t('receipts.received') : t('common.total')}</td>
            <td className="py-2 text-right text-lg font-bold tabular-nums">{money(s.total)}</td>
          </tr>
        </tfoot>
      </table>

      {balanceLines.length > 0 && (
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="border-y border-amber-300 bg-amber-50 text-left">
              <th className="py-2 pl-2 font-medium text-amber-900">{t('receipts.balanceDue')}</th>
              <th className="py-2 pr-2 text-right font-medium text-amber-900">{t('common.amount')}</th>
            </tr>
          </thead>
          <tbody>
            {balanceLines.map((line, index) => (
              <tr key={index} className="border-b border-slate-100">
                <td className="py-2 pl-2">
                  {line.contribution_type}
                  {line.period_month && <span className="text-slate-600"> · {month(line.period_month)}</span>}
                </td>
                <td className="py-2 pr-2 text-right tabular-nums">{money(line.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-amber-700">
              <td className="py-2 pl-2 font-semibold text-amber-900">{t('receipts.balanceDue')}</td>
              <td className="py-2 pr-2 text-right text-lg font-bold tabular-nums text-amber-900">{money(s.balance_total ?? '0')}</td>
            </tr>
          </tfoot>
        </table>
      )}

      <dl className="mt-4 grid gap-1 text-sm">
        <div className="flex gap-2">
          <dt className="w-36 shrink-0 text-slate-500">{t('collect.mode')}</dt>
          <dd>
            {t(`mode.${s.mode}`)}
            {s.reference_number && ` · ${s.reference_number}`}
            {s.cheque_bank && ` · ${s.cheque_bank}`}
          </dd>
        </div>
        {s.collector && (
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-slate-500">{t('receipts.collectedBy')}</dt>
            <dd>{s.collector}</dd>
          </div>
        )}
      </dl>

      <footer className="mt-8 flex items-end justify-between gap-4">
        <p className="text-sm italic text-brand-800">{s.thank_you_message || t('receipts.thankYou')}</p>
        <p className="border-t border-slate-400 pt-1 text-xs text-slate-500">{t('receipts.signature')}</p>
      </footer>
    </article>
  )
}

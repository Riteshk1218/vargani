import i18n from '../i18n'

const LOCALES: Record<string, string> = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' }

export function locale(): string {
  return LOCALES[i18n.language] ?? 'en-IN'
}

/** Money arrives from the API as a decimal string ("1500.00"); never use floats for arithmetic. */
export function formatMoney(value: string | null | undefined, currency = 'INR'): string {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return value
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(number)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}

export function formatMobile(value: string | null | undefined): string {
  if (!value) return ''
  const match = /^\+91(\d{5})(\d{5})$/.exec(value)
  return match ? `+91 ${match[1]} ${match[2]}` : value
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

/** Suggest the Indian financial-year label for a date, e.g. 2026-10-05 → 2026–27 (April to March). */
export function suggestFinancialYear(today = new Date()) {
  const startYear = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1
  return {
    label: `${startYear}–${String((startYear + 1) % 100).padStart(2, '0')}`,
    start_date: `${startYear}-04-01`,
    end_date: `${startYear + 1}-03-31`,
  }
}

/** Exact decimal-string addition in paise (no floating point): ["500", "0.50"] → "500.50". */
export function sumMoney(values: (string | null | undefined)[]): string {
  let paise = 0n
  for (const value of values) {
    const match = /^(-?)(\d*)(?:\.(\d{0,2}))?$/.exec((value ?? '').trim())
    if (!match || (!match[2] && !match[3])) continue
    const amount = BigInt(match[2] || '0') * 100n + BigInt((match[3] ?? '').padEnd(2, '0') || '0')
    paise += match[1] ? -amount : amount
  }
  const negative = paise < 0n
  const abs = negative ? -paise : paise
  return `${negative ? '-' : ''}${abs / 100n}.${String(abs % 100n).padStart(2, '0')}`
}

/** "2027-08-01" → "Aug 2027" in the current language. */
export function formatMonth(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(`${value.slice(0, 7)}-01T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale(), { month: 'short', year: 'numeric' }).format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date)
}

/** Today's date in the browser's time zone, as YYYY-MM-DD (for date inputs). */
export function todayIso(now = new Date()): string {
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 10)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

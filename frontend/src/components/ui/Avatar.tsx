import { initials } from '../../utils/format'
import { cn } from '../../utils/cn'

/** Organization logo, or initials when no logo is uploaded. Never a bundled default logo. */
export function OrgAvatar({ name, logoUrl, size = 'md' }: { name: string; logoUrl?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'size-7 text-xs', md: 'size-9 text-sm', lg: 'size-20 text-2xl' }
  if (logoUrl) return <img src={logoUrl} alt={name} className={cn('shrink-0 rounded-lg bg-white object-contain ring-1 ring-slate-200', sizes[size])} />
  return (
    <span aria-label={name} className={cn('inline-flex shrink-0 items-center justify-center rounded-lg bg-brand-100 font-semibold text-brand-800', sizes[size])}>
      {initials(name)}
    </span>
  )
}

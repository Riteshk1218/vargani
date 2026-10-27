import { Building2, Check } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { ThemeColor } from '../../types/api'
import { cn } from '../../utils/cn'
import { THEME_COLORS, THEME_PALETTES } from '../../utils/theme'

interface Props {
  value: ThemeColor | ''
  onChange: (color: ThemeColor | '') => void
  /** Adds an "Organization color" choice (the empty value), shown in that color. */
  orgColor?: ThemeColor
  disabled?: boolean
}

/** Color swatches. Picking one saves it straight away. */
export function ThemePicker({ value, onChange, orgColor, disabled }: Props) {
  const { t } = useTranslation()
  const swatch = (color: ThemeColor | '', label: string, icon?: ReactNode) => {
    const selected = value === color
    const shades = THEME_PALETTES[color || orgColor || 'orange']
    return (
      <button
        key={color || 'org'}
        type="button"
        role="radio"
        aria-checked={selected}
        aria-label={label}
        title={label}
        disabled={disabled}
        onClick={() => onChange(color)}
        data-testid={`theme-${color || 'org'}`}
        className={cn(
          'group flex flex-col items-center gap-1.5 rounded-xl p-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60',
          selected && 'bg-slate-50 text-slate-900',
        )}
      >
        <span
          className={cn(
            'relative flex size-11 items-center justify-center rounded-full text-white shadow-sm ring-2 ring-offset-2 transition-transform duration-150 group-hover:scale-110 group-active:scale-95',
            selected ? 'ring-slate-900' : 'ring-transparent',
          )}
          style={{ background: `linear-gradient(135deg, ${shades[400]}, ${shades[700]})` }}
        >
          {selected ? <Check className="size-5 drop-shadow" aria-hidden /> : icon}
        </span>
        <span className="max-w-24 truncate">{label}</span>
      </button>
    )
  }
  return (
    <div role="radiogroup" className="flex flex-wrap gap-1">
      {orgColor && swatch('', t('theme.orgDefault'), <Building2 className="size-4" aria-hidden />)}
      {THEME_COLORS.map((color) => swatch(color, t(`theme.colors.${color}`)))}
    </div>
  )
}

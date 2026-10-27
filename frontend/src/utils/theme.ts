import type { ThemeColor } from '../types/api'

type Shade = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900

/** Shades for each app color. The names match the API's `theme_color` values. */
export const THEME_PALETTES: Record<ThemeColor, Record<Shade, string>> = {
  orange: { 50: '#fff7ed', 100: '#ffedd5', 200: '#fed7aa', 300: '#fdba74', 400: '#fb923c', 500: '#f97316', 600: '#ea580c', 700: '#c2410c', 800: '#9a3412', 900: '#7c2d12' },
  red: { 50: '#fef2f2', 100: '#fee2e2', 200: '#fecaca', 300: '#fca5a5', 400: '#f87171', 500: '#ef4444', 600: '#dc2626', 700: '#b91c1c', 800: '#991b1b', 900: '#7f1d1d' },
  maroon: { 50: '#fbf3f3', 100: '#f6e4e4', 200: '#eecbcc', 300: '#e0a3a5', 400: '#cc7175', 500: '#b4484e', 600: '#9a3038', 700: '#80232c', 800: '#6b1f27', 900: '#5b1d24' },
  pink: { 50: '#fdf2f8', 100: '#fce7f3', 200: '#fbcfe8', 300: '#f9a8d4', 400: '#f472b6', 500: '#ec4899', 600: '#db2777', 700: '#be185d', 800: '#9d174d', 900: '#831843' },
  purple: { 50: '#faf5ff', 100: '#f3e8ff', 200: '#e9d5ff', 300: '#d8b4fe', 400: '#c084fc', 500: '#a855f7', 600: '#9333ea', 700: '#7e22ce', 800: '#6b21a8', 900: '#581c87' },
  indigo: { 50: '#eef2ff', 100: '#e0e7ff', 200: '#c7d2fe', 300: '#a5b4fc', 400: '#818cf8', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca', 800: '#3730a3', 900: '#312e81' },
  blue: { 50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a' },
  teal: { 50: '#f0fdfa', 100: '#ccfbf1', 200: '#99f6e4', 300: '#5eead4', 400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e', 800: '#115e59', 900: '#134e4a' },
  green: { 50: '#f0fdf4', 100: '#dcfce7', 200: '#bbf7d0', 300: '#86efac', 400: '#4ade80', 500: '#22c55e', 600: '#16a34a', 700: '#15803d', 800: '#166534', 900: '#14532d' },
}

export const THEME_COLORS = Object.keys(THEME_PALETTES) as ThemeColor[]
export const DEFAULT_THEME: ThemeColor = 'orange'
const STORAGE_KEY = 'vargani.theme'

export function isThemeColor(value: unknown): value is ThemeColor {
  return typeof value === 'string' && value in THEME_PALETTES
}

/** The user's own color wins; otherwise the organization's; otherwise orange. */
export function effectiveTheme(userColor?: string | null, orgColor?: string | null): ThemeColor {
  if (isThemeColor(userColor)) return userColor
  if (isThemeColor(orgColor)) return orgColor
  return DEFAULT_THEME
}

/** Repaint the whole site by swapping the brand color variables. Remembered so the login page matches. */
export function applyTheme(color: ThemeColor) {
  const root = document.documentElement
  for (const [shade, hex] of Object.entries(THEME_PALETTES[color])) root.style.setProperty(`--color-brand-${shade}`, hex)
  root.dataset.theme = color
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_PALETTES[color][700])
  try {
    localStorage.setItem(STORAGE_KEY, color)
  } catch {
    // Private windows may block storage; the color still applies for this visit.
  }
}

export function storedTheme(): ThemeColor {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isThemeColor(value) ? value : DEFAULT_THEME
  } catch {
    return DEFAULT_THEME
  }
}

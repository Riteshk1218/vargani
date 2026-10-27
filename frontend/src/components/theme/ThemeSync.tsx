import { useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useOrg } from '../../context/OrgContext'
import { applyTheme, effectiveTheme, storedTheme } from '../../utils/theme'

/** Keeps the site's colors on the signed-in user's choice, or their organization's color. */
export function ThemeSync() {
  const { user } = useAuth()
  const { detail } = useOrg()
  const userColor = user?.theme_color
  const orgColor = detail?.theme_color
  useEffect(() => {
    // Until the organization loads, keep the last color so the screen does not flash orange.
    if (!userColor && !orgColor) return
    applyTheme(effectiveTheme(userColor, orgColor))
  }, [userColor, orgColor])
  return null
}

applyTheme(storedTheme())

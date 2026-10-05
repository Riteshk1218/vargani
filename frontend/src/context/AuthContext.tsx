import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import i18n from '../i18n'
import { refreshAccessToken, setSessionExpiredHandler } from '../services/apiClient'
import { authService } from '../services/auth'
import { MEMBER_LOGIN_KEY, session } from '../services/session'
import type { TokenResponse, User } from '../types/api'

type Status = 'loading' | 'authenticated' | 'anonymous'

interface AuthValue {
  status: Status
  user: User | null
  startSession: (tokens: TokenResponse) => void
  logout: () => Promise<void>
  setUser: (user: User) => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<Status>('loading')
  const [user, setUserState] = useState<User | null>(null)

  const applyUser = useCallback((next: User) => {
    setUserState(next)
    if (next.preferred_language && next.preferred_language !== i18n.language) {
      void i18n.changeLanguage(next.preferred_language)
      session.setLanguage(next.preferred_language)
    }
  }, [])

  const clear = useCallback(() => {
    session.setAccessToken(null)
    setUserState(null)
    setStatus('anonymous')
    queryClient.clear()
  }, [queryClient])

  useEffect(() => {
    setSessionExpiredHandler(clear)
    let cancelled = false
    // Restore the session from the HttpOnly refresh cookie, if there is one.
    refreshAccessToken().then(async (token) => {
      if (cancelled) return
      if (!token) {
        setStatus('anonymous')
        return
      }
      try {
        applyUser(await authService.me())
        setStatus('authenticated')
      } catch {
        clear()
      }
    })
    return () => {
      cancelled = true
    }
  }, [applyUser, clear])

  const startSession = useCallback(
    (tokens: TokenResponse) => {
      session.setAccessToken(tokens.access)
      applyUser(tokens.user)
      setStatus('authenticated')
    },
    [applyUser],
  )

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      session.setOrganizationId(null)
      session.write(MEMBER_LOGIN_KEY, null)
      clear()
    }
  }, [clear])

  const value = useMemo(() => ({ status, user, startSession, logout, setUser: applyUser }), [status, user, startSession, logout, applyUser])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}

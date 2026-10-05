/**
 * In-memory session values used by the API client. The access token is never written to storage;
 * the refresh token lives in an HttpOnly cookie set by the API.
 */
import type { Language } from '../types/api'

const ORG_KEY = 'vargani.activeOrg'
const LANG_KEY = 'vargani.language'

let accessToken: string | null = null
let organizationId: string | null = readStorage(ORG_KEY)

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, value)
  } catch {
    /* storage unavailable (private mode); keep in memory only */
  }
}

export const session = {
  getAccessToken: () => accessToken,
  setAccessToken: (token: string | null) => {
    accessToken = token
  },
  getOrganizationId: () => organizationId,
  setOrganizationId: (id: string | null) => {
    organizationId = id
    writeStorage(ORG_KEY, id)
  },
  getLanguage: (): Language => (readStorage(LANG_KEY) as Language | null) ?? 'en',
  setLanguage: (language: Language) => writeStorage(LANG_KEY, language),
  eventKey: (orgId: string) => `vargani.activeEvent.${orgId}`,
  read: readStorage,
  write: writeStorage,
}

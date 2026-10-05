import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import en from '../i18n/locales/en/common.json'
import hi from '../i18n/locales/hi/common.json'
import mr from '../i18n/locales/mr/common.json'

function flatten(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix]
  return Object.entries(value).flatMap(([key, child]) => flatten(child, prefix ? `${prefix}.${key}` : key))
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return name === 'test' ? [] : sourceFiles(path)
    return /\.(tsx?)$/.test(name) ? [path] : []
  })
}

describe('translations', () => {
  const enKeys = new Set(flatten(en))

  it.each([
    ['mr', mr],
    ['hi', hi],
  ])('%s has exactly the same keys as English', (_, locale) => {
    expect(new Set(flatten(locale))).toEqual(enKeys)
  })

  it('every static key used in the code exists', () => {
    const root = join(__dirname, '..')
    const used = new Set<string>()
    for (const file of sourceFiles(root)) {
      const text = readFileSync(file, 'utf8')
      for (const match of text.matchAll(/\bt\('([a-zA-Z0-9_.]+)'/g)) used.add(match[1])
      for (const match of text.matchAll(/label: '([a-z]+\.[a-zA-Z0-9_.]+)'/g)) used.add(match[1])
    }
    const missing = [...used].filter((key) => !enKeys.has(key))
    expect(missing).toEqual([])
  })

  it('has every role, status, person type and module used by the API', () => {
    for (const key of ['org_admin', 'treasurer', 'secretary', 'collector', 'volunteer', 'member']) expect(enKeys.has(`roles.${key}`)).toBe(true)
    for (const key of ['active', 'draft', 'closed', 'archived', 'suspended']) expect(enKeys.has(`status.${key}`)).toBe(true)
    for (const key of ['member', 'karyakarta', 'volunteer', 'donor', 'supporter', 'other']) expect(enKeys.has(`personType.${key}`)).toBe(true)
    for (const key of ['contributions', 'monthly', 'expenses', 'collectors', 'member_portal']) expect(enKeys.has(`events.module.${key}`)).toBe(true)
  })
})

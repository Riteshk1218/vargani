import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useToast } from '../components/ui/Toast'
import { toApiError } from '../services/apiClient'

/** Puts field errors from the API next to the matching form fields; anything else becomes a toast. */
export function useApiErrors<T extends FieldValues>(setError?: UseFormSetError<T>, fields: string[] = []) {
  const { notify } = useToast()
  const { t } = useTranslation()
  return (error: unknown) => {
    const apiError = toApiError(error)
    let placed = false
    if (setError) {
      for (const [field, messages] of Object.entries(apiError.details)) {
        if (fields.includes(field) && messages[0]) {
          setError(field as Path<T>, { type: 'server', message: messages[0] })
          placed = true
        }
      }
    }
    if (!placed) notify(apiError.message || t('errors.generic'), 'error')
    return apiError
  }
}

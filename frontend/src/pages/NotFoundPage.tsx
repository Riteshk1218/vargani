import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/States'

export function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <EmptyState
      title={t('errors.notFoundTitle')}
      message={t('errors.notFound')}
      action={
        <Link to="/app/dashboard" className="text-sm font-medium text-brand-700 hover:underline">
          {t('nav.dashboard')}
        </Link>
      }
    />
  )
}

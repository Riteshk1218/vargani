import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { ErrorState, FullPageSpinner } from '../../components/ui/States'
import { API_BASE_URL } from '../../services/apiClient'
import { receiptService } from '../../services/finance'
import { ReceiptView } from './ReceiptView'

/** Opened from a WhatsApp link by the contributor. No login. */
export function PublicReceiptPage() {
  const { t } = useTranslation()
  const { token = '' } = useParams()
  const receipt = useQuery({ queryKey: ['public-receipt', token], queryFn: () => receiptService.public(token), retry: false })
  if (receipt.isLoading) return <FullPageSpinner />
  if (receipt.isError) {
    return (
      <div className="mx-auto max-w-md p-6">
        <ErrorState message={t('receipts.linkInvalid')} />
      </div>
    )
  }
  return (
    <div className="min-h-screen bg-slate-100 px-3 py-6 sm:py-10">
      <div className="mx-auto max-w-2xl overflow-hidden rounded-xl shadow-sm ring-1 ring-slate-200">
        <ReceiptView receipt={receipt.data!} />
      </div>
      <div className="mt-4 text-center print:hidden">
        <a href={`${API_BASE_URL}/public/receipts/${token}/pdf/`}>
          <Button icon={<Download className="size-4" />}>{t('receipts.downloadPdf')}</Button>
        </a>
      </div>
    </div>
  )
}

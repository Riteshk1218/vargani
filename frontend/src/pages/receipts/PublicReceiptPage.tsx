import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { ErrorState, FullPageSpinner } from '../../components/ui/States'
import { API_BASE_URL } from '../../services/apiClient'
import { receiptService } from '../../services/finance'
import { ReceiptLanguagePicker, ReceiptView } from './ReceiptView'

/** Opened from a WhatsApp link by the contributor. No login. */
export function PublicReceiptPage() {
  const { t } = useTranslation()
  const { token = '' } = useParams()
  const receipt = useQuery({ queryKey: ['public-receipt', token], queryFn: () => receiptService.public(token), retry: false })
  const [chosenLanguage, setLanguage] = useState<string>()
  if (receipt.isLoading) return <FullPageSpinner />
  if (receipt.isError) {
    return (
      <div className="mx-auto max-w-md p-6">
        <ErrorState message={t('receipts.linkInvalid')} />
      </div>
    )
  }
  const language = chosenLanguage ?? receipt.data!.language ?? 'en'
  return (
    <div className="min-h-screen bg-slate-100 px-3 py-6 sm:py-10">
      <div className="mx-auto mb-3 flex max-w-2xl justify-end print:hidden">
        <ReceiptLanguagePicker value={language} onChange={setLanguage} />
      </div>
      <div className="mx-auto max-w-2xl overflow-hidden rounded-xl shadow-sm ring-1 ring-slate-200">
        <ReceiptView receipt={receipt.data!} language={language} />
      </div>
      <div className="mt-4 text-center print:hidden">
        <a href={`${API_BASE_URL}/public/receipts/${token}/pdf/?language=${language}`}>
          <Button icon={<Download className="size-4" />}>{t('receipts.downloadPdf')}</Button>
        </a>
      </div>
    </div>
  )
}

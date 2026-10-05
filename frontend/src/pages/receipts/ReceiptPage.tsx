import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Printer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ErrorState, Spinner } from '../../components/ui/States'
import { useOrg } from '../../context/OrgContext'
import { receiptService } from '../../services/finance'
import { ReceiptView } from './ReceiptView'

export function ReceiptPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const { activeOrgId } = useOrg()
  const receipt = useQuery({ queryKey: ['org', activeOrgId, 'receipts', 'detail', id], queryFn: () => receiptService.get(id) })

  if (receipt.isLoading) return <Spinner />
  if (receipt.isError) return <ErrorState message={t('errors.notFound')} />
  return (
    <div>
      <div className="mb-4 flex items-center justify-between print:hidden">
        <Link to="/app/receipts" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" /> {t('receipts.title')}
        </Link>
        <Button icon={<Printer className="size-4" />} onClick={() => window.print()}>
          {t('common.print')}
        </Button>
      </div>
      <Card className="overflow-hidden print:shadow-none print:ring-0">
        <ReceiptView receipt={receipt.data!} />
      </Card>
      <p className="mt-3 text-center text-xs text-slate-500 print:hidden">{t('receipts.printHint')}</p>
    </div>
  )
}

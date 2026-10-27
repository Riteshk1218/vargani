import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Ban, Download, MessageCircle, Pencil, Printer, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { ErrorState, Spinner } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { paymentService, receiptService, saveBlob } from '../../services/finance'
import { PaymentEditModal } from '../payments/PaymentEditModal'
import { ReceiptLanguagePicker, ReceiptView } from './ReceiptView'

export function ReceiptPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const { activeOrgId, can } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [voiding, setVoiding] = useState(false)
  const [reason, setReason] = useState('')
  const [chosenLanguage, setLanguage] = useState<string>()
  const [editing, setEditing] = useState(false)
  const key = ['org', activeOrgId, 'receipts', 'detail', id]
  const receipt = useQuery({ queryKey: key, queryFn: () => receiptService.get(id) })
  const language = chosenLanguage ?? receipt.data?.language ?? 'en'
  const canEdit = can('records.admin_edit') && receipt.data?.status === 'issued'
  const payment = useQuery({
    queryKey: ['org', activeOrgId, 'payments', 'detail', receipt.data?.payment],
    queryFn: () => paymentService.get(receipt.data!.payment),
    enabled: editing && Boolean(receipt.data?.payment),
  })

  const download = useMutation({
    mutationFn: () => receiptService.pdf(id, language),
    onSuccess: (blob) => saveBlob(blob, `${receipt.data?.receipt_number ?? 'receipt'}.pdf`),
    onError,
  })
  const share = useMutation({
    mutationFn: () => receiptService.share(id, language),
    onSuccess: (link) => {
      window.open(link.whatsapp_url, '_blank', 'noopener')
      void navigator.clipboard?.writeText(link.share_url).catch(() => undefined)
      notify(t('receipts.shareReady'))
    },
    onError,
  })
  const requestVoid = useMutation({
    mutationFn: () => receiptService.requestVoid(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('receipts.voidRequested'))
      setVoiding(false)
      setReason('')
    },
    onError,
  })

  if (receipt.isLoading) return <Spinner />
  if (receipt.isError) return <ErrorState message={t('errors.notFound')} />
  const r = receipt.data!
  const issued = r.status === 'issued'

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Link to="/app/receipts" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" /> {t('receipts.title')}
        </Link>
        <div className="flex flex-wrap gap-2">
          <ReceiptLanguagePicker value={language} onChange={setLanguage} />
          {canEdit && (
            <Button variant="secondary" icon={<Pencil className="size-4" />} loading={editing && payment.isLoading} onClick={() => setEditing(true)}>
              {t('receipts.edit')}
            </Button>
          )}
          {issued && can('receipts.share') && (
            <Button icon={<MessageCircle className="size-4" />} loading={share.isPending} onClick={() => share.mutate()}>
              {t('receipts.whatsapp')}
            </Button>
          )}
          <Button variant="secondary" icon={<Download className="size-4" />} loading={download.isPending} onClick={() => download.mutate()}>
            {t('receipts.downloadPdf')}
          </Button>
          <Button variant="secondary" icon={<Printer className="size-4" />} onClick={() => window.print()}>
            {t('common.print')}
          </Button>
          {issued && !r.pending_void_request && can('receipts.void_request') && (
            <Button variant="ghost" icon={<Ban className="size-4" />} onClick={() => setVoiding(true)}>
              {t('receipts.requestVoid')}
            </Button>
          )}
        </div>
      </div>
      {r.pending_void_request && (
        <div className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200 print:hidden">
          {t('receipts.voidPending', { reason: r.pending_void_request.reason })}{' '}
          {can('receipts.void_approve') && (
            <Link to="/app/approvals" className="font-medium underline">
              {t('approvals.open')}
            </Link>
          )}
        </div>
      )}
      {r.status === 'void' && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-900 ring-1 ring-red-200 print:hidden">
          <span>
            {t('receipts.voidBanner', { reason: r.void_reason })}
            {r.replaced_by && (
              <>
                {' '}
                <Link className="font-medium underline" to={`/app/receipts/${r.replaced_by.id}`}>
                  {t('receipts.replacedBy', { number: r.replaced_by.receipt_number })}
                </Link>
              </>
            )}
          </span>
          {!r.replaced_by && can('receipts.void_approve') && can('payments.create') && (
            <Link to={`/app/collect?event=${r.event}&person=${r.payer}&replaces=${r.id}`}>
              <Button size="sm" icon={<RotateCcw className="size-4" />}>
                {t('receipts.recordCorrection')}
              </Button>
            </Link>
          )}
        </div>
      )}
      {r.replaces_receipt && (
        <p className="mb-3 text-sm text-slate-600 print:hidden">
          {t('receipts.replaces')}{' '}
          <Link className="font-medium text-brand-700 underline" to={`/app/receipts/${r.replaces_receipt}`}>
            {r.replaces_receipt_number}
          </Link>
        </p>
      )}
      <Card className="overflow-hidden print:shadow-none print:ring-0">
        <ReceiptView receipt={r} language={language} />
      </Card>
      {editing && payment.data && (
        <PaymentEditModal
          payment={payment.data}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            void queryClient.invalidateQueries({ queryKey: key })
          }}
        />
      )}
      <Modal
        open={voiding}
        title={t('receipts.requestVoid')}
        onClose={() => setVoiding(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setVoiding(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="danger" loading={requestVoid.isPending} disabled={!reason.trim()} onClick={() => requestVoid.mutate()}>
              {t('receipts.sendVoidRequest')}
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-sm">
          <p>{t('receipts.voidExplain', { number: r.receipt_number })}</p>
          <TextInput label={t('payments.reason')} required value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>
    </div>
  )
}

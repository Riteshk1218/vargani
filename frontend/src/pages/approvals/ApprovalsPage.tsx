import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { SelectInput, TextInput } from '../../components/ui/Field'
import { Modal } from '../../components/ui/Modal'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { receiptService } from '../../services/finance'
import type { VoidRequest } from '../../types/api'
import { formatDateTime, formatMoney } from '../../utils/format'

const TONE = { pending: 'amber', approved: 'red', rejected: 'gray' } as const

/** Receipt void requests waiting for a decision (and their history). */
export function ApprovalsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { activeOrgId, detail, can } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const [deciding, setDeciding] = useState<{ request: VoidRequest; decision: 'approve' | 'reject' } | null>(null)
  const [note, setNote] = useState('')
  const requests = useQuery({
    queryKey: ['org', activeOrgId, 'void-requests', status, page],
    queryFn: () => receiptService.voidRequests({ status: status || undefined, page }),
  })
  const decide = useMutation({
    mutationFn: () => receiptService.decideVoid(deciding!.request.id, deciding!.decision, note),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId] })
      notify(t('common.saved'))
      setDeciding(null)
      setNote('')
    },
    onError,
  })
  const currency = detail?.organization.currency
  const canDecide = can('receipts.void_approve')

  return (
    <div>
      <PageHeader title={t('approvals.title')} description={t('approvals.subtitle')} />
      <Card>
        <div className="border-b border-slate-200 p-4 sm:w-60">
          <SelectInput label={t('common.status')} value={status} onChange={(e) => (setStatus(e.target.value), setPage(1))}>
            <option value="pending">{t('approvals.status.pending')}</option>
            <option value="approved">{t('approvals.status.approved')}</option>
            <option value="rejected">{t('approvals.status.rejected')}</option>
            <option value="">{t('common.all')}</option>
          </SelectInput>
        </div>
        {requests.isLoading ? (
          <SkeletonRows />
        ) : requests.isError ? (
          <ErrorState onRetry={() => void requests.refetch()} />
        ) : requests.data!.count === 0 ? (
          <EmptyState icon={<ShieldCheck className="size-6" />} title={t('approvals.empty')} />
        ) : (
          <>
            <ul className="divide-y divide-slate-100">
              {requests.data!.results.map((r) => (
                <li key={r.id} className="flex cursor-pointer flex-col gap-2 px-4 py-3 text-sm hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between" onClick={() => navigate(`/app/receipts/${r.receipt}`)}>
                  <div className="min-w-0">
                    <p className="font-medium">
                      <Link className="font-mono text-brand-700 hover:underline" to={`/app/receipts/${r.receipt}`}>
                        {r.receipt_number}
                      </Link>{' '}
                      · {r.payer_name} · {formatMoney(r.amount, currency)}
                    </p>
                    <p className="text-slate-600">“{r.reason}”</p>
                    <p className="text-xs text-slate-500">
                      {t('approvals.requestedBy', { name: r.requested_by_name, when: formatDateTime(r.created_at) })}
                      {r.decided_by_name && ` · ${t('approvals.decidedBy', { name: r.decided_by_name })}`}
                    </p>
                  </div>
                  {r.status === 'pending' && canDecide ? (
                    <div className="flex shrink-0 gap-2" onClick={(e) => e.stopPropagation()}>
                      <Button size="sm" variant="secondary" icon={<X className="size-4" />} onClick={() => setDeciding({ request: r, decision: 'reject' })}>
                        {t('approvals.reject')}
                      </Button>
                      <Button size="sm" variant="danger" icon={<Check className="size-4" />} onClick={() => setDeciding({ request: r, decision: 'approve' })}>
                        {t('approvals.approve')}
                      </Button>
                    </div>
                  ) : (
                    <Badge tone={TONE[r.status]}>{t(`approvals.status.${r.status}`)}</Badge>
                  )}
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={25} count={requests.data!.count} onChange={setPage} />
          </>
        )}
      </Card>
      <Modal
        open={deciding !== null}
        title={deciding?.decision === 'approve' ? t('approvals.approveTitle') : t('approvals.rejectTitle')}
        onClose={() => setDeciding(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeciding(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant={deciding?.decision === 'approve' ? 'danger' : 'primary'} loading={decide.isPending} onClick={() => decide.mutate()}>
              {deciding?.decision === 'approve' ? t('approvals.approve') : t('approvals.reject')}
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-sm">
          {deciding?.decision === 'approve' && <p>{t('approvals.approveMessage', { number: deciding.request.receipt_number })}</p>}
          <TextInput label={t('approvals.note')} hint={t('common.optional')} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
        </div>
      </Modal>
    </div>
  )
}

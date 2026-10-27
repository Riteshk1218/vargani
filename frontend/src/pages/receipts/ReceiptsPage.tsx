import { useQuery } from '@tanstack/react-query'
import { ReceiptText, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Badge, Card, PageHeader } from '../../components/ui/Card'
import { TextInput } from '../../components/ui/Field'
import { Pagination } from '../../components/ui/Pagination'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { useDebounced } from '../../hooks/useDebounced'
import { receiptService } from '../../services/finance'
import { formatMoney, formatStamp } from '../../utils/format'
import { DownloadMenu } from '../../components/DownloadMenu'
import { CreatedMeta, ListTools, useListTools } from '../../components/ListTools'

export function ReceiptsPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail } = useOrg()
  const { activeEvent } = useEvents()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const tools = useListTools('-issued_at', () => setPage(1))
  const debounced = useDebounced(search)
  const eventId = activeEvent?.id
  const receipts = useQuery({
    queryKey: ['org', activeOrgId, 'receipts', 'list', eventId, debounced, tools.query, page],
    queryFn: () => receiptService.list({ event: eventId, search: debounced || undefined, ...tools.query, page }),
    enabled: Boolean(eventId),
  })
  const currency = detail?.organization.currency

  return (
    <div>
      <PageHeader title={t('receipts.title')} description={activeEvent ? `${activeEvent.name} · ${t('receipts.subtitle')}` : t('receipts.subtitle')} actions={<DownloadMenu path="/receipts/" params={{ event: eventId, search: debounced, ...tools.query }} />} />
      <Card>
        {!eventId ? (
          <EmptyState title={t('common.selectEvent')} message={t('common.selectEventMessage')} />
        ) : (
          <>
            <div className="relative border-b border-slate-200 p-4">
              <TextInput label={t('common.search')} placeholder={t('receipts.searchPlaceholder')} value={search} onChange={(e) => (setSearch(e.target.value), setPage(1))} />
              <Search className="pointer-events-none absolute right-7 top-13 size-4 text-slate-400" aria-hidden />
            </div>
            <ListTools
              tools={tools}
              sortOptions={[
                { field: 'issued_at', label: t('common.date') },
                { field: 'sequence', label: t('receipts.number') },
                { field: 'payment__amount', label: t('common.amount') },
                { field: 'payment__payer__full_name', label: t('people.fullName') },
              ]}
            />
            {receipts.isLoading ? (
              <SkeletonRows />
            ) : receipts.isError ? (
              <ErrorState onRetry={() => void receipts.refetch()} />
            ) : receipts.data!.count === 0 ? (
              <EmptyState icon={<ReceiptText className="size-6" />} title={debounced || tools.filtered ? t('people.noMatches') : t('receipts.empty')} message={debounced || tools.filtered ? undefined : t('receipts.emptyMessage')} />
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {receipts.data!.results.map((r) => (
                    <li key={r.id}>
                      <Link to={`/app/receipts/${r.id}`} className="flex items-center justify-between gap-3 px-4 py-3 text-sm hover:bg-slate-50">
                        <div className="min-w-0">
                          <p className="font-mono font-medium">{r.receipt_number}</p>
                          <p className="truncate text-slate-600">
                            {r.payer_name} · {formatStamp(r.paid_at ?? r.issued_at)}
                          </p>
                          <CreatedMeta at={r.created_at ?? r.issued_at} by={r.created_by_name} />
                        </div>
                        <div className="text-right">
                          <p className="font-semibold tabular-nums">{formatMoney(r.amount, currency)}</p>
                          {r.status === 'void' ? <Badge tone="red">{t('receipts.void')}</Badge> : <span className="text-xs text-slate-500">{t(`mode.${r.mode}`)}</span>}
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
                <Pagination page={page} pageSize={25} count={receipts.data!.count} onChange={setPage} />
              </>
            )}
          </>
        )}
      </Card>
    </div>
  )
}

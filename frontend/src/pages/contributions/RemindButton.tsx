import { useMutation } from '@tanstack/react-query'
import { BellRing, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { reminderService } from '../../services/portal'
import type { ReminderResult } from '../../types/api'
import { formatMobile, formatMoney } from '../../utils/format'

/** Reminds everyone who still owes: in the app when they have a login, otherwise with a WhatsApp message to tap. */
export function RemindButton({ contributionTypeId }: { contributionTypeId: string }) {
  const { t } = useTranslation()
  const { detail } = useOrg()
  const onError = useApiErrors()
  const [result, setResult] = useState<ReminderResult | null>(null)
  const remind = useMutation({ mutationFn: () => reminderService.send(contributionTypeId), onSuccess: setResult, onError })
  const currency = detail?.organization.currency
  return (
    <>
      <Button size="sm" variant="secondary" icon={<BellRing className="size-4" />} loading={remind.isPending} onClick={() => remind.mutate()}>
        {t('reminders.send')}
      </Button>
      <Modal open={result !== null} title={t('reminders.title')} onClose={() => setResult(null)} footer={<Button onClick={() => setResult(null)}>{t('common.close')}</Button>}>
        {result && (
          <div className="space-y-3 text-sm">
            <p>{t('reminders.inApp', { count: result.notified })}</p>
            {result.already_reminded > 0 && <p className="text-slate-500">{t('reminders.already', { count: result.already_reminded })}</p>}
            {result.whatsapp.length > 0 && (
              <>
                <p className="font-medium">{t('reminders.whatsappIntro', { count: result.whatsapp.length })}</p>
                <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-lg ring-1 ring-slate-200">
                  {result.whatsapp.map((w) => (
                    <li key={w.person} className="flex items-center justify-between gap-3 px-3 py-2">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{w.name}</p>
                        <p className="text-xs text-slate-500">
                          {formatMobile(w.mobile)} · {formatMoney(w.due, currency)}
                        </p>
                      </div>
                      <a
                        href={w.whatsapp_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                      >
                        <MessageCircle className="size-3.5" /> WhatsApp
                      </a>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </Modal>
    </>
  )
}

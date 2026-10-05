import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Card'
import { Checkbox, TextInput } from '../../components/ui/Field'
import { ErrorState, SkeletonRows } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { toApiError } from '../../services/apiClient'
import { gatewayService, type GatewayInput } from '../../services/portal'
import type { GatewaySettings } from '../../types/api'

/** Razorpay keys for online payments by members. Secrets are never shown again after saving. */
export function PaymentGatewayPanel() {
  const { activeOrgId } = useOrg()
  const config = useQuery({ queryKey: ['org', activeOrgId, 'gateway'], queryFn: gatewayService.get })
  if (config.isLoading) return <SkeletonRows rows={4} />
  if (config.isError) return <ErrorState onRetry={() => void config.refetch()} />
  return <GatewayForm key={JSON.stringify(config.data)} current={config.data!} />
}

function GatewayForm({ current }: { current: GatewaySettings }) {
  const { t } = useTranslation()
  const { activeOrgId } = useOrg()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [keyId, setKeyId] = useState(current.key_id)
  const [keySecret, setKeySecret] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [active, setActive] = useState(current.is_active)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const save = useMutation({
    mutationFn: () => {
      const input: GatewayInput = { key_id: keyId.trim(), is_active: active }
      if (keySecret) input.key_secret = keySecret
      if (webhookSecret) input.webhook_secret = webhookSecret
      return gatewayService.save(input)
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['org', activeOrgId, 'gateway'], data)
      notify(t('common.saved'))
    },
    onError: (error) => {
      const apiError = toApiError(error)
      setErrors(Object.fromEntries(Object.entries(apiError.details).map(([k, v]) => [k, v[0]])))
      if (Object.keys(apiError.details).length === 0) notify(apiError.message, 'error')
    },
  })
  const secretHint = (has: boolean) => (has ? t('gateway.secretSaved') : t('gateway.secretMissing'))
  return (
    <form className="max-w-xl space-y-4" onSubmit={(e) => (e.preventDefault(), setErrors({}), save.mutate())}>
      <div className="flex items-center gap-2">
        <h2 className="font-semibold">Razorpay</h2>
        <Badge tone={current.is_active ? 'green' : 'gray'}>{current.is_active ? t('gateway.on') : t('gateway.off')}</Badge>
      </div>
      <p className="text-sm text-slate-600">{t('gateway.help')}</p>
      <TextInput label={t('gateway.keyId')} placeholder="rzp_live_…" value={keyId} error={errors.key_id} autoComplete="off" onChange={(e) => setKeyId(e.target.value)} />
      <TextInput label={t('gateway.keySecret')} type="password" autoComplete="new-password" hint={secretHint(current.has_key_secret)} value={keySecret} error={errors.key_secret} onChange={(e) => setKeySecret(e.target.value)} />
      <TextInput label={t('gateway.webhookSecret')} type="password" autoComplete="new-password" hint={secretHint(current.has_webhook_secret)} value={webhookSecret} error={errors.webhook_secret} onChange={(e) => setWebhookSecret(e.target.value)} />
      {current.webhook_url && (
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-700">{t('gateway.webhookUrl')}</p>
          <div className="flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg bg-slate-100 px-3 py-2 text-xs">{current.webhook_url}</code>
            <Button size="sm" variant="secondary" icon={<Copy className="size-4" />} onClick={() => void navigator.clipboard.writeText(current.webhook_url).then(() => notify(t('common.copied')))}>
              {t('gateway.copy')}
            </Button>
          </div>
          <p className="text-xs text-slate-500">{t('gateway.webhookHelp')}</p>
        </div>
      )}
      <Checkbox label={t('gateway.active')} description={t('gateway.activeHelp')} checked={active} onChange={(e) => setActive(e.target.checked)} />
      {errors.is_active && <p className="text-sm text-red-600">{errors.is_active}</p>}
      <Button type="submit" loading={save.isPending}>
        {t('common.save')}
      </Button>
    </form>
  )
}

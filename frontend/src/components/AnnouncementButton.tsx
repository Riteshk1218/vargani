import { useMutation } from '@tanstack/react-query'
import { Megaphone } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useApiErrors } from '../hooks/useApiErrors'
import { notificationService } from '../services/portal'
import { Button } from './ui/Button'
import { TextArea, TextInput } from './ui/Field'
import { Modal } from './ui/Modal'
import { useToast } from './ui/Toast'

/** Send a short message to everyone with access to this organization (shown in their notifications). */
export function AnnouncementButton() {
  const { t } = useTranslation()
  const { notify } = useToast()
  const onError = useApiErrors()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const send = useMutation({
    mutationFn: () => notificationService.announce(title.trim(), message.trim()),
    onSuccess: (data) => {
      notify(t('announce.sent', { count: data.sent }))
      setTitle('')
      setMessage('')
      setOpen(false)
    },
    onError,
  })
  return (
    <>
      <Button variant="secondary" icon={<Megaphone className="size-4" />} onClick={() => setOpen(true)}>
        {t('announce.button')}
      </Button>
      <Modal
        open={open}
        title={t('announce.title')}
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button loading={send.isPending} disabled={!title.trim() || !message.trim()} onClick={() => send.mutate()}>
              {t('announce.send')}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-600">{t('announce.help')}</p>
          <TextInput label={t('announce.subject')} required maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextArea label={t('announce.message')} required rows={4} maxLength={1000} value={message} onChange={(e) => setMessage(e.target.value)} />
        </div>
      </Modal>
    </>
  )
}

import { useQueryClient } from '@tanstack/react-query'
import { ImageUp, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { OrgAvatar } from '../../components/ui/Avatar'
import { Button } from '../../components/ui/Button'
import { Checkbox } from '../../components/ui/Field'
import { ConfirmDialog } from '../../components/ui/Modal'
import { useToast } from '../../components/ui/Toast'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { organizationService } from '../../services/organizations'
import type { Organization } from '../../types/api'

const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp']
const MAX_BYTES = 5 * 1024 * 1024

/** Centre-crops an image to a square on a canvas so logos look right on receipts and in the app. */
async function cropToSquare(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file)
  const side = Math.min(bitmap.width, bitmap.height)
  const output = Math.min(side, 1024)
  const canvas = document.createElement('canvas')
  canvas.width = output
  canvas.height = output
  const context = canvas.getContext('2d')!
  context.drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, output, output)
  return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('crop'))), 'image/png'))
}

export function LogoUploader({ organization }: { organization: Organization }) {
  const { t } = useTranslation()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const { activeOrgId } = useOrg()
  const onError = useApiErrors()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [square, setSquare] = useState(true)
  const [saving, setSaving] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState(false)

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const choose = (chosen: File | undefined) => {
    if (!chosen) return
    if (!ACCEPTED.includes(chosen.type)) return notify(t('logo.wrongType'), 'error')
    if (chosen.size > MAX_BYTES) return notify(t('logo.tooLarge'), 'error')
    setFile(chosen)
    setPreview(URL.createObjectURL(chosen))
  }

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['org', activeOrgId, 'me'] })
    await queryClient.invalidateQueries({ queryKey: ['me', 'organizations'] })
  }

  const upload = async () => {
    if (!file) return
    setSaving(true)
    try {
      const blob = square ? await cropToSquare(file) : file
      await organizationService.uploadLogo(organization.id, blob, square ? 'logo.png' : file.name)
      await refresh()
      setFile(null)
      setPreview(null)
      notify(t('logo.saved'))
    } catch (error) {
      onError(error)
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    setSaving(true)
    try {
      await organizationService.removeLogo(organization.id)
      await refresh()
      setConfirmRemove(false)
      notify(t('logo.removed'))
    } catch (error) {
      onError(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
      <div className="flex flex-col items-center gap-2">
        {preview ? (
          <img src={preview} alt={t('logo.preview')} className={`size-32 rounded-xl bg-white ring-1 ring-slate-200 ${square ? 'object-cover' : 'object-contain'}`} />
        ) : (
          <div className="flex size-32 items-center justify-center">
            <OrgAvatar name={organization.name} logoUrl={organization.logo_url} size="lg" />
          </div>
        )}
        <span className="text-xs text-slate-500">{preview ? t('logo.preview') : t('logo.current')}</span>
      </div>
      <div className="flex-1 space-y-3">
        <p className="text-sm text-slate-600">{t('logo.help')}</p>
        <input ref={input} type="file" accept={ACCEPTED.join(',')} className="hidden" onChange={(e) => choose(e.target.files?.[0])} />
        {file ? (
          <>
            <Checkbox label={t('logo.cropSquare')} checked={square} onChange={(e) => setSquare(e.target.checked)} />
            <div className="flex gap-2">
              <Button loading={saving} onClick={() => void upload()}>
                {t('logo.save')}
              </Button>
              <Button variant="secondary" onClick={() => (setFile(null), setPreview(null))}>
                {t('common.cancel')}
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" icon={<ImageUp className="size-4" />} onClick={() => input.current?.click()}>
              {organization.logo_url ? t('logo.replace') : t('logo.upload')}
            </Button>
            {organization.logo_url && (
              <Button variant="ghost" icon={<Trash2 className="size-4" />} onClick={() => setConfirmRemove(true)}>
                {t('logo.remove')}
              </Button>
            )}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirmRemove}
        title={t('logo.removeTitle')}
        message={t('logo.removeMessage')}
        confirmLabel={t('logo.remove')}
        danger
        loading={saving}
        onConfirm={() => void remove()}
        onClose={() => setConfirmRemove(false)}
      />
    </div>
  )
}

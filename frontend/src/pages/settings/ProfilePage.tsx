import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { LanguageSelector } from '../../components/layout/LanguageSelector'
import { Button } from '../../components/ui/Button'
import { Card, PageHeader } from '../../components/ui/Card'
import { TextInput } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../context/AuthContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { authService } from '../../services/auth'
import { formatMobile } from '../../utils/format'

export function ProfilePage() {
  const { t } = useTranslation()
  const { user, setUser, startSession } = useAuth()
  const { notify } = useToast()
  const nameForm = useForm({ defaultValues: { full_name: user?.full_name ?? '' } })
  const passwordForm = useForm({ defaultValues: { current_password: '', new_password: '' } })
  const onNameError = useApiErrors(nameForm.setError, ['full_name'])
  const onPasswordError = useApiErrors(passwordForm.setError, ['current_password', 'new_password'])
  if (!user) return null

  return (
    <div className="space-y-6">
      <PageHeader title={t('profile.title')} description={user.email ?? formatMobile(user.mobile)} />
      <Card className="space-y-4 p-5">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={nameForm.handleSubmit(async (values) => {
            try {
              setUser(await authService.updateMe(values))
              notify(t('common.saved'))
            } catch (error) {
              onNameError(error)
            }
          })}
        >
          <TextInput className="flex-1" label={t('auth.fullName')} error={nameForm.formState.errors.full_name?.message} {...nameForm.register('full_name', { required: true })} />
          <Button type="submit" loading={nameForm.formState.isSubmitting}>
            {t('common.save')}
          </Button>
        </form>
        <div>
          <p className="mb-1 text-sm font-medium text-slate-700">{t('topbar.language')}</p>
          <LanguageSelector />
        </div>
      </Card>
      <Card className="p-5">
        <h2 className="mb-4 font-semibold">{t('profile.changePassword')}</h2>
        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={passwordForm.handleSubmit(async (values) => {
            try {
              startSession(await authService.changePassword(values.current_password, values.new_password))
              passwordForm.reset()
              notify(t('profile.passwordChanged'))
            } catch (error) {
              onPasswordError(error)
            }
          })}
        >
          <TextInput label={t('profile.currentPassword')} type="password" autoComplete="current-password" error={passwordForm.formState.errors.current_password?.message} {...passwordForm.register('current_password', { required: true })} />
          <TextInput label={t('auth.newPassword')} type="password" autoComplete="new-password" hint={t('auth.passwordHint')} error={passwordForm.formState.errors.new_password?.message} {...passwordForm.register('new_password', { required: true })} />
          <div className="sm:col-span-2">
            <Button type="submit" loading={passwordForm.formState.isSubmitting}>
              {t('profile.changePassword')}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { OrgAvatar } from '../../components/ui/Avatar'
import { Button } from '../../components/ui/Button'
import { ErrorState, Spinner } from '../../components/ui/States'
import { useAuth } from '../../context/AuthContext'
import { useOrg } from '../../context/OrgContext'
import { useApiErrors } from '../../hooks/useApiErrors'
import { memberService } from '../../services/organizations'

export function AcceptInvitePage() {
  const { t } = useTranslation()
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { status } = useAuth()
  const { switchOrganization } = useOrg()
  const onError = useApiErrors()
  const [accepting, setAccepting] = useState(false)
  const preview = useQuery({ queryKey: ['invitation', token], queryFn: () => memberService.previewInvitation(token) })

  if (preview.isLoading || status === 'loading') return <Spinner />
  if (preview.isError) return <ErrorState onRetry={() => void preview.refetch()} />
  if (!preview.data?.valid) return <ErrorState message={t('invite.invalid')} />
  const { organization, role } = preview.data

  const accept = async () => {
    setAccepting(true)
    try {
      const membership = await memberService.acceptInvitation(token)
      await queryClient.invalidateQueries({ queryKey: ['me', 'organizations'] })
      switchOrganization(membership.id)
      navigate('/app/dashboard', { replace: true })
    } catch (error) {
      onError(error)
    } finally {
      setAccepting(false)
    }
  }

  return (
    <div className="space-y-5 text-center">
      <div className="flex justify-center">
        <OrgAvatar name={organization!.name} logoUrl={organization!.logo_url} size="lg" />
      </div>
      <div>
        <h1 className="text-xl font-semibold">{t('invite.title', { organization: organization!.name })}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('invite.role', { role: t(`roles.${role!.code}`, role!.name) })}</p>
      </div>
      {status === 'authenticated' ? (
        <Button className="w-full" loading={accepting} onClick={() => void accept()}>
          {t('invite.accept')}
        </Button>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-slate-600">{t('invite.loginFirst')}</p>
          <div className="flex gap-2">
            <Link to="/login" state={{ from: `/invite/${token}` }} className="flex-1">
              <Button variant="secondary" className="w-full">
                {t('auth.login')}
              </Button>
            </Link>
            <Link to="/register" className="flex-1">
              <Button className="w-full">{t('auth.registerLink')}</Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

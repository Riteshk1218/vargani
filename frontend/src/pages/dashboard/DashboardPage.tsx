import { useQuery } from '@tanstack/react-query'
import { CalendarDays, CalendarPlus, IndianRupee, ShieldCheck, UserPlus, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { Card, PageHeader, StatCard } from '../../components/ui/Card'
import { EmptyState, ErrorState, SkeletonRows } from '../../components/ui/States'
import { useEvents } from '../../context/EventContext'
import { useOrg } from '../../context/OrgContext'
import { dashboardService } from '../../services/dashboard'
import { formatMoney } from '../../utils/format'

export function DashboardPage() {
  const { t } = useTranslation()
  const { activeOrgId, detail, can } = useOrg()
  const { activeEvent } = useEvents()
  const summary = useQuery({
    queryKey: ['org', activeOrgId, 'dashboard', activeEvent?.id ?? 'none'],
    queryFn: () => dashboardService.summary(activeEvent?.id),
  })

  const org = detail!.organization
  return (
    <div>
      <PageHeader title={t('dashboard.title')} description={activeEvent ? t('dashboard.forEvent', { event: activeEvent.name }) : org.name} />
      {summary.isLoading ? (
        <Card>
          <SkeletonRows rows={3} />
        </Card>
      ) : summary.isError ? (
        <Card>
          <ErrorState onRetry={() => void summary.refetch()} />
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t('dashboard.events')} value={summary.data!.events.total} hint={t('dashboard.activeCount', { count: summary.data!.events.active })} icon={<CalendarDays className="size-5" />} />
            {summary.data!.people && (
              <StatCard label={t('dashboard.people')} value={summary.data!.people.total} hint={t('dashboard.activeCount', { count: summary.data!.people.active })} icon={<Users className="size-5" />} />
            )}
            {summary.data!.members && <StatCard label={t('dashboard.users')} value={summary.data!.members.total} icon={<ShieldCheck className="size-5" />} />}
            {activeEvent?.target_amount && <StatCard label={t('dashboard.target')} value={formatMoney(activeEvent.target_amount, org.currency)} icon={<IndianRupee className="size-5" />} />}
          </div>

          {can('dashboard.view_financial') && (
            <Card>
              <EmptyState
                icon={<IndianRupee className="size-6" />}
                title={t('dashboard.noCollectionsTitle')}
                message={t('dashboard.noCollectionsMessage')}
              />
            </Card>
          )}

          {summary.data!.events.total === 0 && can('events.manage') && (
            <Card>
              <EmptyState
                icon={<CalendarPlus className="size-6" />}
                title={t('dashboard.firstEventTitle')}
                message={t('dashboard.firstEventMessage')}
                action={
                  <Link to="/app/events?new=1">
                    <Button icon={<CalendarPlus className="size-4" />}>{t('events.create')}</Button>
                  </Link>
                }
              />
            </Card>
          )}
          {summary.data!.people?.total === 0 && can('people.manage') && (
            <Card>
              <EmptyState
                icon={<UserPlus className="size-6" />}
                title={t('dashboard.firstPersonTitle')}
                message={t('dashboard.firstPersonMessage')}
                action={
                  <Link to="/app/people?new=1">
                    <Button icon={<UserPlus className="size-4" />}>{t('people.add')}</Button>
                  </Link>
                }
              />
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

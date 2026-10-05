import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { notificationService } from '../../services/portal'
import type { AppNotification } from '../../types/api'
import { cn } from '../../utils/cn'
import { formatDateTime } from '../../utils/format'
import { Popover } from '../ui/Popover'

/** My notifications from every organization. The count refreshes every minute while the page is open. */
export function NotificationBell() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const unread = useQuery({ queryKey: ['me', 'notifications', 'unread'], queryFn: notificationService.unreadCount, refetchInterval: 60_000 })
  const list = useQuery({ queryKey: ['me', 'notifications', 'list'], queryFn: () => notificationService.list(), enabled: false })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['me', 'notifications'] })
  const markAll = useMutation({ mutationFn: notificationService.readAll, onSuccess: refresh })
  const open = async (n: AppNotification, close: () => void) => {
    close()
    if (!n.read_at) await notificationService.read(n.id).catch(() => undefined)
    refresh()
    if (n.link.startsWith('/app/')) navigate(n.link)
  }
  const count = unread.data ?? 0
  return (
    <Popover
      align="right"
      label={count > 0 ? t('notifications.labelUnread', { count }) : t('notifications.label')}
      trigger={(isOpen) => {
        return (
          <span className="relative inline-flex size-9 items-center justify-center rounded-full text-slate-600 hover:bg-slate-100" onClick={() => !isOpen && void list.refetch()}>
            <Bell className="size-5" aria-hidden />
            {count > 0 && (
              <span className="absolute -right-0.5 -top-0.5 min-w-5 rounded-full bg-red-600 px-1 text-center text-[11px] font-semibold leading-5 text-white">{count > 99 ? '99+' : count}</span>
            )}
          </span>
        )
      }}
    >
      {(close) => (
        <div className="w-80 max-w-[calc(100vw-2rem)]">
          <div className="flex items-center justify-between px-3 py-2">
            <p className="text-sm font-semibold">{t('notifications.title')}</p>
            {count > 0 && (
              <button type="button" className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline" onClick={() => markAll.mutate()}>
                <CheckCheck className="size-3.5" /> {t('notifications.markAll')}
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto border-t border-slate-100">
            {!list.data ? (
              <p className="px-3 py-6 text-center text-sm text-slate-500">{t('common.loading')}</p>
            ) : (list.data?.results.length ?? 0) === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-slate-500">{t('notifications.empty')}</p>
            ) : (
              <ul>
                {list.data!.results.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => void open(n, close)}
                      className={cn('block w-full px-3 py-2.5 text-left hover:bg-slate-50', !n.read_at && 'bg-brand-50/60')}
                    >
                      <p className="flex items-center gap-2 text-sm font-medium">
                        {!n.read_at && <span className="size-2 shrink-0 rounded-full bg-brand-600" aria-hidden />}
                        <span className="truncate">{n.title}</span>
                      </p>
                      {n.body && <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">{n.body}</p>}
                      <p className="mt-0.5 text-[11px] text-slate-400">
                        {formatDateTime(n.created_at)}
                        {n.organization_name && ` · ${n.organization_name}`}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Popover>
  )
}

import { Link } from 'react-router-dom';
import { Bell, CheckCheck, Inbox, Trash2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { formatRelativeTime } from '@/lib/formatters';
import { useNotifications } from '@/features/notifications/hooks/useNotifications';
import type { AppNotification, NotificationSeverity } from '@/types';

const SEVERITY_DOT: Record<NotificationSeverity, string> = {
  info: 'bg-blue-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
};

function NotificationRow({
  notification,
  onDismiss,
  onOpen,
}: {
  notification: AppNotification;
  onDismiss: (id: string) => void;
  onOpen: (id: string) => void;
}) {
  const content = (
    <div
      className={cn(
        'group relative flex gap-3 rounded-lg px-3 py-2.5 pr-9 transition-colors hover:bg-muted/60',
        !notification.read && 'bg-blue-50/60 dark:bg-blue-950/20',
      )}
    >
      <span
        className={cn(
          'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
          notification.read ? 'bg-transparent' : SEVERITY_DOT[notification.severity],
        )}
      />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'truncate text-xs',
            notification.read ? 'font-medium text-foreground/80' : 'font-semibold text-foreground',
          )}
        >
          {notification.title}
        </p>
        <p className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-muted-foreground">
          {notification.description}
        </p>
        <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/70">
          {formatRelativeTime(notification.createdAt)}
        </p>
      </div>

      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onDismiss(notification.id);
        }}
        aria-label="Eliminar notificación"
        className="absolute right-2 top-2.5 rounded-md p-1 text-muted-foreground/60 opacity-0 transition-opacity hover:bg-background hover:text-destructive group-hover:opacity-100"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );

  if (notification.href) {
    return (
      <Link to={notification.href} onClick={() => onOpen(notification.id)} className="block">
        {content}
      </Link>
    );
  }
  return (
    <div onClick={() => onOpen(notification.id)} className="cursor-default">
      {content}
    </div>
  );
}

export function NotificationsMenu() {
  const { notifications, unreadCount, dismiss, clearAll, markAsRead, markAllAsRead } =
    useNotifications();

  return (
    <DropdownMenu>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative h-9 w-9 text-muted-foreground hover:text-foreground"
                aria-label="Notificaciones del sistema"
              >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold leading-none text-primary-foreground">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent>
            <span>
              {unreadCount > 0 ? `${unreadCount} notificaciones sin leer` : 'Notificaciones'}
            </span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <DropdownMenuContent align="end" className="w-80 p-0 sm:w-96">
        <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
          <span className="text-xs font-bold text-foreground">Notificaciones</span>
          {notifications.length > 0 && (
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={markAllAsRead}
                  className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] font-medium text-primary hover:bg-primary/10"
                >
                  <CheckCheck className="h-3 w-3" />
                  Marcar leídas
                </button>
              )}
              <button
                type="button"
                onClick={clearAll}
                className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="h-3 w-3" />
                Limpiar
              </button>
            </div>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
            <Inbox className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-xs font-medium text-muted-foreground">No tienes notificaciones</p>
          </div>
        ) : (
          <div className="max-h-96 overflow-y-auto p-1.5">
            {notifications.map((notification) => (
              <NotificationRow
                key={notification.id}
                notification={notification}
                onDismiss={dismiss}
                onOpen={markAsRead}
              />
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export type NotificationSeverity = 'info' | 'success' | 'warning';

export interface AppNotification {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  read: boolean;
  severity: NotificationSeverity;
  href?: string;
}

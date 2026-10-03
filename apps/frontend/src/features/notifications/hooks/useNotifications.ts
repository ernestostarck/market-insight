import { useCallback, useEffect, useState } from 'react';
import { STORAGE_KEYS } from '@/lib/constants';
import type { AppNotification } from '@/types';

// Seed data: there is no backend notification feed yet, so the panel starts with a
// representative set instead of being empty on every first load. Anything the user
// dismisses is gone for good (persisted in localStorage), which is the whole point.
const SEED_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'seed-1',
    title: '3 licitaciones con cambios hoy',
    description: 'Fechas de cierre o montos estimados actualizados por ChileCompra.',
    createdAt: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
    read: false,
    severity: 'info',
    href: '/licitaciones',
  },
  {
    id: 'seed-2',
    title: 'Nueva adjudicación relevante',
    description: 'Ortopedia Austral SpA fue adjudicada en "Equipos geriátricos hospital regional".',
    createdAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    read: false,
    severity: 'success',
    href: '/adjudicaciones',
  },
  {
    id: 'seed-3',
    title: 'Calidad de datos en revisión',
    description: 'Se detectaron 2 registros con RUT inválido en la última sincronización.',
    createdAt: new Date(Date.now() - 26 * 60 * 60 * 1000).toISOString(),
    read: true,
    severity: 'warning',
  },
];

function loadNotifications(): AppNotification[] {
  if (typeof window === 'undefined') return SEED_NOTIFICATIONS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS.notifications);
    if (raw === null) return SEED_NOTIFICATIONS;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : SEED_NOTIFICATIONS;
  } catch {
    return SEED_NOTIFICATIONS;
  }
}

function persist(notifications: AppNotification[]) {
  try {
    window.localStorage.setItem(STORAGE_KEYS.notifications, JSON.stringify(notifications));
  } catch {
    // Best effort: private browsing / storage disabled shouldn't break the panel.
  }
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>(loadNotifications);

  useEffect(() => {
    persist(notifications);
  }, [notifications]);

  const dismiss = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, unreadCount, dismiss, clearAll, markAsRead, markAllAsRead };
}

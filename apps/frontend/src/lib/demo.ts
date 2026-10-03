import type { User } from '@/features/auth/types';

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';
export const DEMO_TOKEN = 'demo-token';

export const DEMO_USER: User = {
  id: 'demo',
  email: 'visitante@demo.mercadoinsight.cl',
  full_name: 'Visitante Demo',
  job_title: 'Explorando MercadoInsight',
  role: 'analyst',
  is_active: true,
  mfa_enabled: false,
  preferences: {
    theme: 'system',
    default_page_size: 25,
    landing_page: '/dashboard',
    default_segmento: null,
    compact_tables: false,
  },
  created_at: '2026-01-01T00:00:00Z',
  last_login_at: null,
  last_login_ip: null,
  password_changed_at: null,
};

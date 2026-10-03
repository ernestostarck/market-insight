import type { User } from '@/features/auth/types';

/** A signed-in user with the profile fields the hardened /auth/me returns. */
export const MOCK_USER: User = {
  id: '3b046957-d30a-43f7-84d8-7099e3b1120d',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  job_title: null,
  role: 'admin',
  is_active: true,
  mfa_enabled: false,
  preferences: {
    theme: 'system',
    default_page_size: 10,
    landing_page: '/dashboard',
    default_segmento: null,
    compact_tables: false,
  },
  created_at: '2026-08-19T21:06:35Z',
  last_login_at: null,
  last_login_ip: null,
  password_changed_at: null,
};

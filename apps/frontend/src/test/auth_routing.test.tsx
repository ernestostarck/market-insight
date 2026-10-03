import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MOCK_USER } from './mockAuth';

import { loginSchema } from '@/features/auth/schemas';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';
import { AuthContext } from '@/features/auth/context/AuthContext';

describe('Auth & Routing Modules', () => {
  describe('loginSchema validation', () => {
    it('rejects invalid email formats', () => {
      const result = loginSchema.safeParse({
        email: 'invalid-email',
        password: 'password123',
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.errors[0].message).toContain('correo electrónico');
      }
    });

    it('rejects short passwords (< 6 chars)', () => {
      const result = loginSchema.safeParse({
        email: 'admin@chilecompra.cl',
        password: '123',
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.errors[0].message).toContain('6 caracteres');
      }
    });

    it('accepts valid credentials', () => {
      const result = loginSchema.safeParse({
        email: 'analista@marketinsight.cl',
        password: 'secretPassword123',
      });
      expect(result.success).toBe(true);
    });
  });

  describe('ProtectedRoute Component', () => {
    it('redirects to /login when user is not authenticated', () => {
      const mockAuthValue = {
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        login: async () => ({ status: 'authenticated' as const }),
        verifyMfa: async () => {},
        logout: async () => {},
        checkAuth: async () => {},
        setUser: () => {},
      };

      render(
        <AuthContext.Provider value={mockAuthValue}>
          <MemoryRouter initialEntries={['/dashboard']}>
            <Routes>
              <Route path="/login" element={<div>Pantalla de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>,
      );

      expect(screen.getByText('Pantalla de Login')).toBeInTheDocument();
      expect(screen.queryByText('Dashboard Protegido')).not.toBeInTheDocument();
    });

    it('renders protected child when authenticated', () => {
      const mockAuthValue = {
        user: MOCK_USER,
        token: 'mock-valid-jwt-token',
        isAuthenticated: true,
        isLoading: false,
        login: async () => ({ status: 'authenticated' as const }),
        verifyMfa: async () => {},
        logout: async () => {},
        checkAuth: async () => {},
        setUser: () => {},
      };

      render(
        <AuthContext.Provider value={mockAuthValue}>
          <MemoryRouter initialEntries={['/dashboard']}>
            <Routes>
              <Route path="/login" element={<div>Pantalla de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>,
      );

      expect(screen.getByText('Dashboard Protegido')).toBeInTheDocument();
    });
  });

  describe('NotFoundPage Component', () => {
    it('renders 404 title and navigation buttons', () => {
      render(
        <MemoryRouter>
          <NotFoundPage />
        </MemoryRouter>,
      );

      expect(screen.getByText('404')).toBeInTheDocument();
      expect(screen.getByText('Página no encontrada')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /volver atrás/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /ir al dashboard/i })).toBeInTheDocument();
    });
  });
});

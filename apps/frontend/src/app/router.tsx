import React, { Suspense } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';

// Subphase 7.29: Code splitting with React.lazy() for optimal performance & chunk size reduction
const LoginPage = React.lazy(() =>
  import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })),
);
const DashboardPage = React.lazy(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const LicitacionesPage = React.lazy(() =>
  import('@/pages/LicitacionesPage').then((m) => ({ default: m.LicitacionesPage })),
);
const LicitacionDetailPage = React.lazy(() =>
  import('@/pages/LicitacionDetailPage').then((m) => ({ default: m.LicitacionDetailPage })),
);
const SearchPage = React.lazy(() =>
  import('@/pages/SearchPage').then((m) => ({ default: m.SearchPage })),
);
const ProveedoresPage = React.lazy(() =>
  import('@/pages/ProveedoresPage').then((m) => ({ default: m.ProveedoresPage })),
);
const ProveedorDetailPage = React.lazy(() =>
  import('@/pages/ProveedorDetailPage').then((m) => ({ default: m.ProveedorDetailPage })),
);
const OrganismosPage = React.lazy(() =>
  import('@/pages/OrganismosPage').then((m) => ({ default: m.OrganismosPage })),
);
const OrganismoDetailPage = React.lazy(() =>
  import('@/pages/OrganismoDetailPage').then((m) => ({ default: m.OrganismoDetailPage })),
);
const CategoriasPage = React.lazy(() =>
  import('@/pages/CategoriasPage').then((m) => ({ default: m.CategoriasPage })),
);
const RubrosPage = React.lazy(() =>
  import('@/pages/RubrosPage').then((m) => ({ default: m.RubrosPage })),
);
const MarketObjectivePage = React.lazy(() =>
  import('@/pages/MarketObjectivePage').then((m) => ({ default: m.MarketObjectivePage })),
);
const AdjudicacionesPage = React.lazy(() =>
  import('@/pages/AdjudicacionesPage').then((m) => ({ default: m.AdjudicacionesPage })),
);
const OrdenesCompraPage = React.lazy(() =>
  import('@/pages/OrdenesCompraPage').then((m) => ({ default: m.OrdenesCompraPage })),
);
const AnalyticsPage = React.lazy(() =>
  import('@/pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })),
);
const AIPage = React.lazy(() =>
  import('@/pages/AIPage').then((m) => ({ default: m.AIPage })),
);
const ProfilePage = React.lazy(() =>
  import('@/pages/ProfilePage').then((m) => ({ default: m.ProfilePage })),
);
const SettingsPage = React.lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
);
const NotFoundPage = React.lazy(() =>
  import('@/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })),
);
const GenericModulePage = React.lazy(() =>
  import('@/pages/GenericModulePage').then((m) => ({ default: m.GenericModulePage })),
);

function PageLoadingFallback() {
  return (
    <div className="flex h-[50vh] w-full items-center justify-center" role="status" aria-label="Cargando módulo">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-xs font-medium">Cargando módulo de inteligencia...</span>
      </div>
    </div>
  );
}

function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <Suspense fallback={<PageLoadingFallback />}>
          <Outlet />
        </Suspense>
      </AppLayout>
    </ProtectedRoute>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<PageLoadingFallback />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected App Routes */}
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Licitaciones */}
          <Route path="/licitaciones" element={<LicitacionesPage />} />
          <Route path="/licitaciones/:id" element={<LicitacionDetailPage />} />

          {/* Mercado Overview & Target Market */}
          <Route path="/mercado" element={<MarketObjectivePage />} />
          <Route path="/market/disability-geriatrics" element={<MarketObjectivePage />} />

          {/* Proveedores */}
          <Route path="/proveedores" element={<ProveedoresPage />} />
          <Route path="/proveedores/:id" element={<ProveedorDetailPage />} />

          {/* Organismos */}
          <Route path="/organismos" element={<OrganismosPage />} />
          <Route path="/organismos/:id" element={<OrganismoDetailPage />} />

          {/* Categorías */}
          <Route path="/categorias" element={<CategoriasPage />} />
          <Route
            path="/categorias/:id"
            element={
              <GenericModulePage
                title="Detalle de Categoría"
                description="Demanda agregada, precios de referencia y evolución por segmento de producto."
              />
            }
          />

          {/* Rubros de mercado (sectores/taxonomía de clasificación NLP, ej. Vestuario) */}
          <Route path="/rubros" element={<RubrosPage />} />

          {/* Adjudicaciones & Órdenes de Compra */}
          <Route path="/adjudicaciones" element={<AdjudicacionesPage />} />
          <Route path="/ordenes-compra" element={<OrdenesCompraPage />} />

          {/* Analytics & Search */}
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/search" element={<SearchPage />} />

          {/* Subphase 7.26 - 7.28: IA / NLP, Human-in-the-Loop & Calidad de Datos */}
          <Route path="/ai" element={<AIPage />} />

          {/* Cuenta */}
          <Route path="/perfil" element={<ProfilePage />} />
          <Route path="/configuracion" element={<SettingsPage />} />
        </Route>

        {/* 404 Not Found Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}

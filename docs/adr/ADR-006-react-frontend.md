# ADR-006: Uso de React 18, TypeScript y Tailwind CSS en el Frontend

- **Status**: Aceptado
- **Fecha**: 2026-09-05
- **Decisores**: Equipo de Frontend y UX

---

## Contexto
El frontend de MercadoInsight debe presentar tableros interactivos con visualización de datos de alta densidad (series temporales, gráficos de dispersión, mapas territoriales, tablas virtualizadas con miles de licitaciones) y una interfaz de chat con streaming continuo.

## Decisión
Construir el frontend como una Single Page Application (SPA) basada en **React 18**, **TypeScript**, **Vite** como empaquetador ultrarrápido, **Tailwind CSS** para el sistema de diseño, **TanStack Query** para la gestión de estado de servidor y **Zustand** para el estado de cliente.

## Alternativas Consideradas
1. **Next.js (SSR / Server Components)**: Excelente para SEO y renderizado en servidor, pero añade complejidad operacional de servidor Node.js en producción. MercadoInsight es una aplicación analítica protegida por autenticación donde el SEO público no es el factor determinante.
2. **Vue 3 / Nuxt**: Ecosistema limpio y reactivo, pero menor disponibilidad de librerías especializadas para tablas analíticas masivas y visualización geoespacial avanzada en comparación con el ecosistema React.
3. **Plantillas del Servidor (Jinja2 + HTMX)**: Muy ligero, pero insuficiente para la interactividad reactiva fluida requerida por gráficos interactivos de ECharts y el streaming SSE del asistente de IA.

## Consecuencias
- **Positivas**:
  - Compilación a archivos estáticos puros (`HTML`, `JS`, `CSS`) servibles directamente por NGINX con mínimo consumo de recursos en producción.
  - Seguridad estricta de tipos en contratos de datos compartidos con el backend gracias a TypeScript.
  - Excelente experiencia de desarrollo con Hot Module Replacement (HMR) instantáneo mediante Vite.
- **Negativas**:
  - La carga inicial del bundle requiere optimización de code-splitting para mantener el First Contentful Paint (FCP) bajo control.

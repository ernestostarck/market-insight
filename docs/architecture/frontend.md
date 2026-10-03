# Arquitectura del Frontend — React SPA

Este documento describe la arquitectura de la aplicación de usuario de **MercadoInsight** (`apps/frontend`), implementada como una Single Page Application (SPA) en **React 18** con **TypeScript**, **Vite** y **Tailwind CSS**.

---

## 1. Estructura del Proyecto

```text
apps/frontend/
├── src/
│   ├── app/                # Configuración global, providers y enrutador
│   ├── assets/             # Íconos, logotipos y recursos estáticos
│   ├── components/         # Componentes reutilizables
│   │   ├── charts/         # Gráficos interactivos (ECharts, Leaflet)
│   │   ├── feedback/       # Notificaciones, spinners, modales
│   │   ├── filters/        # Barras de filtrado y facetas de búsqueda
│   │   ├── layout/         # Sidebar, Navbar, PageContainer
│   │   └── ui/             # Componentes base (Botones, Inputs, Badges)
│   ├── features/           # Módulos organizados por dominio de negocio
│   │   ├── adjudicaciones/ # Vistas y tablas de adjudicaciones
│   │   ├── ai/             # Asistente conversacional RAG
│   │   ├── auth/           # Login, recuperación de sesión y tokens
│   │   ├── etl/            # Monitoreo y estado de pipelines
│   │   ├── licitaciones/   # Explorador y fichas de licitaciones
│   │   └── suppliers/      # Perfiles de proveedores y organismos
│   ├── hooks/              # Hooks personalizados (debounce, media query, auth)
│   ├── pages/              # Páginas principales accesibles por ruta
│   ├── schemas/            # Validación Zod para formularios y respuestas
│   ├── stores/             # Gestión de estado global con Zustand
│   └── types/              # Definiciones TypeScript compartidas
```

---

## 2. Gestión de Estado y Comunicación con la API

La aplicación distingue entre estado de servidor (Server State) y estado de cliente (Client State):

1. **Estado de Servidor (`TanStack Query / React Query`)**:
   - Caching inteligente con tiempo de vida configurable (`staleTime: 5min`).
   - Deduplicación automática de peticiones en vuelo.
   - Paginación y filtrado sincronizados con la URL mediante query parameters.
   - Mutaciones optimistas con invalidación selectiva de queries afectadas.

2. **Estado de Cliente (`Zustand`)**:
   - Estado de autenticación (`useAuthStore`): tokens JWT, usuario activo y roles.
   - Preferencias de interfaz (modo oscuro/claro, estado colapsado del menú lateral).
   - Filtros temporales del dashboard analítico.

---

## 3. Streaming y Experiencia de IA Conversacional

Para la interfaz del Asistente RAG (`/ai`):
- Consumo de streaming en tiempo real vía **Server-Sent Events (SSE)**.
- Renderizado interactivo de tokens a medida que son generados por el LLM.
- Presentación diferenciada de **Fuentes Citadas** (*Sources*): licitaciones, RUTs de proveedores y montos con enlaces directos a sus fichas operativas.
- Componente de feedback humano (`ThumbsUp / ThumbsDown` y correcciones) para mejora continua del modelo.

---

## 4. Visualización y Accesibilidad

- **Gráficos**: Integración con **Apache ECharts** para visualización de series temporales de gasto público, distribución por rubro y diagramas de dispersión de ofertas.
- **Georreferenciación**: Mapas con **Leaflet** mostrando distribución territorial de adjudicaciones por región y comuna en Chile.
- **Tablas de Alto Rendimiento**: Tablas virtualizadas para soportar miles de registros de licitaciones sin degradar el DOM.
- **Accesibilidad (a11y)**: Cumplimiento de directrices WCAG 2.1 AA (contraste de colores, soporte completo de teclado y etiquetas semánticas ARIA).

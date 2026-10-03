# Pipeline de Frontend — MercadoInsight

Este documento detalla los controles de calidad, pruebas unitarias, compilación, pruebas end-to-end y empaquetado ejecutados por el workflow [`frontend.yml`](file:///c:/Users/artut/market-insight/.github/workflows/frontend.yml).

---

## 1. Etapas del Pipeline

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 1. Instalación│ ──> │  2. Calidad  │ ──> │ 3. Unit Tests│ ──> │4. Build Vite │
│   (npm ci)   │     │(ESLint + tsc)│     │   (Vitest)   │     │(dist estático)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                                                                       ▼
                                                               ┌──────────────┐
                                                               │ 5. E2E Tests │
                                                               │ (Playwright) │
                                                               └──────────────┘
                                                                       │
                                                                       ▼
                                                               ┌──────────────┐
                                                               │6. Build Docker│
                                                               │(NGINX Alpine)│
                                                               └──────────────┘
```

---

## 2. Descripción Detallada de Controles

### 2.1 Instalación Determinista (`npm ci`)
* **Comando**:
  ```bash
  npm ci
  ```
* **Ventaja**: Garantiza que las dependencias instaladas en el agente de CI coincidan byte por byte con el archivo `package-lock.json`, eliminando divergencias entre entornos de desarrollo y de compilación.

### 2.2 Linter y Verificación de Tipos (`eslint` y `tsc`)
* **Linter**:
  ```bash
  npm run lint
  ```
  Evalúa reglas de React Hooks, componentes funcionales y estándares de TypeScript en `src/**/*.{ts,tsx}`.
* **Typecheck Estático**:
  ```bash
  npm run typecheck
  ```
  Ejecuta el compilador de TypeScript (`tsc --noEmit`) para validar que todos los tipos, interfaces, esquemas Zod y llamadas a API coincidan con las firmas esperadas sin emitir archivos.

### 2.3 Pruebas Unitarias de Componentes (`vitest`)
* **Herramienta**: Vitest con entorno de DOM virtual (`jsdom`) y `@testing-library/react`.
* **Comando**:
  ```bash
  npm run test
  ```
* **Cobertura**: Valida renderizado de componentes KPI, manejo de estado en filtros, hooks personalizados de consulta a la API y formateadores de datos chilenos (moneda CLP, RUT, fechas).

### 2.4 Compilación de Producción (Vite)
* **Comando**:
  ```bash
  npm run build
  ```
* **Salida**: Genera la carpeta optimizada `apps/frontend/dist/` con chunks separados para dependencias (`vendor-react`, `vendor-query`, `vendor-ui`), minificación y hashing de assets para caché inmutable.
* **Artefactos**: Se publica el contenido de `dist/` como artefacto de GitHub Actions para auditoría previa al despliegue.

### 2.5 Pruebas End-to-End (Playwright)
* **Herramienta**: Playwright con navegadores Chromium headless.
* **Comando**:
  ```bash
  npm run test:e2e
  ```
* **Flujos Verificados**: Navegación principal, autenticación, carga del dashboard, filtros de búsqueda de licitaciones y renderizado de gráficos.

### 2.6 Empaquetado en NGINX Alpine
* Compilación multi-stage con [`apps/frontend/Dockerfile.prod`](file:///c:/Users/artut/market-insight/apps/frontend/Dockerfile.prod).
* La imagen final resultante no contiene Node.js, pesando menos de **45MB** y lista para ser servida por NGINX perimetral.
* Publicación automática en `ghcr.io/ernestostarck/market-insight/frontend`.

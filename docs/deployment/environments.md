# Estrategia de Entornos — MercadoInsight

Este documento formaliza la definición, segmentación, asignación de recursos, políticas de datos y estrategia de promoción entre los cuatro entornos de **MercadoInsight**: `development`, `testing`, `staging` y `production`.

---

## 1. Visión General de Entornos

MercadoInsight sigue una arquitectura desacoplada y reproducible basada en contenedores Docker y configuraciones de doce factores. Cada entorno cumple un propósito específico dentro del ciclo de vida del software:

```text
┌──────────────┐      Pull Request / CI      ┌─────────────┐
│ development  │ ──────────────────────────> │   testing   │
└──────────────┘                             └─────────────┘
                                                    │
                                     Merged to main │ Automated Deploy
                                                    ▼
┌──────────────┐      Manual Gate Approval   ┌─────────────┐
│  production  │ <────────────────────────── │   staging   │
└──────────────┘                             └─────────────┘
```

---

## 2. Definición Detallada de Entornos

### 2.1 Development (Desarrollo Local)
* **Propósito**: Iteración rápida para desarrolladores, depuración interactiva y pruebas de componentes individuales.
* **Orquestación**: `docker compose -f docker-compose.yml -f docker/compose/docker-compose.dev.yml up -d` (o `make dev-up`).
* **Puntos de Entrada**:
  - Frontend SPA: `http://localhost:5173` (Vite dev server con HMR).
  - API Backend: `http://localhost:8000` (FastAPI con `uvicorn --reload`).
  - pgAdmin: `http://localhost:5050` (gestión visual de PostgreSQL).
  - RedisInsight: `http://localhost:5540` (análisis de claves y colas Celery).
  - MinIO Console: `http://localhost:9001` (explorador de buckets S3).
* **Parámetros**:
  - `LOG_LEVEL=DEBUG`, `LOG_FORMAT=console` (salida coloreada y formateada para terminal).
  - `RATE_LIMIT_ENABLED=false` (evita bloqueos durante desarrollo intensivo).
  - Observabilidad avanzada opcional con perfil `--profile observability-full`.
* **Políticas de Datos**:
  - Datos sintéticos generados localmente mediante fixtures o scrapers controlados.
  - **Prohibido terminantemente** volcar respaldos de producción que contengan PII o datos comerciales reales sin anonimización previa.

---

### 2.2 Testing (Pruebas Automatizadas y CI)
* **Propósito**: Ejecución determinista de la suite de pruebas unitarias, de integración, de regresión y smoke tests en un entorno completamente aislado y reproducible.
* **Orquestación**: `infrastructure/scripts/test-env.sh` o `docker compose -p mercadoinsight-test -f docker-compose.yml -f docker/compose/docker-compose.test.yml up -d` (o `make test-env`).
* **Topología**:
  - Proyecto Docker aislado (`mercadoinsight-test`), evitando colisiones con contenedores de desarrollo.
  - **Puertos cerrados hacia el host** (`ports: !reset []`): solo los contenedores dentro de la red interna se comunican.
  - Workers de ETL periódicos desactivados (`profiles: ["disabled"]`) para prevenir llamadas automáticas accidentales a la API pública de ChileCompra.
  - Base de datos temporal `market_insight_test` recreada o migrada limpiamente en cada ciclo.
* **Herramientas de Test**:
  - Backend: `pytest` con cobertura, `junit.xml` emitido a `test-results/`.
  - Frontend: `vitest` para componentes y hooks, `playwright` para flujos end-to-end.
* **Políticas de Datos**:
  - Fixtures reproducibles y versionados en código (`tests/fixtures/`).
  - Respuestas HTTP cacheadas o mockeadas para servicios externos (ChileCompra, LLM APIs).

---

### 2.3 Staging (Pre-producción y Homologación)
* **Propósito**: Réplica fiel de la infraestructura de producción para validación final previa al release (validación de carga, verificación de migraciones Alembic, compatibilidad de proxy TLS, pruebas de regresión visual y auditoría de seguridad).
* **Orquestación**: `docker compose --env-file .env.staging -f docker-compose.yml -f docker/compose/docker-compose.staging.yml up -d --build` (o `make staging-up`).
* **Topología**:
  - NGINX como **único servicio expuesto** (puertos `80` y `443` con redirección forzada a HTTPS).
  - Todos los servicios de datos y lógica interna (PostgreSQL, Redis, MinIO, API, Celery Workers, Prometheus, Loki) están estrictamente confinados a la red privada `mercadoinsight`.
  - Herramientas de depuración (`pgAdmin`, `RedisInsight`) desactivadas permanentemente.
  - Monitoreo activo: Grafana (`/grafana/`) y Alertmanager (`/alertmanager/`) protegidos con autenticación Basic Auth detrás de NGINX.
* **Parámetros**:
  - `LOG_LEVEL=INFO`, `LOG_FORMAT=json` (formato JSON estructurado para agregación en Loki).
  - `RATE_LIMIT_ENABLED=true` (prueba de límites de tasa reales).
  - `SENTRY_ENVIRONMENT=staging` con sampleo de trazas del 50%.
* **Políticas de Datos**:
  - Conjunto de datos representativo pre-productivo.
  - Sanitización estricta de cualquier identificador personal o información sensible.

---

### 2.4 Production (Producción Operacional)
* **Propósito**: Servicio estable, seguro, observable y altamente disponible para los usuarios finales y analistas de mercado.
* **Orquestación**: `docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d --build` (o `make prod-up`).
* **Topología**:
  - NGINX perimetral con certificados TLS comerciales o Let's Encrypt, cifrado moderno (TLSv1.2, TLSv1.3) y cabeceras de seguridad estrictas (HSTS, Content-Security-Policy, X-Content-Type-Options).
  - Contenedores optimizados de producción multi-stage: runtime mínimo en distroless/alpine sin paquetes de compilación.
  - Observabilidad integral: Prometheus con retención de 30 días, Loki para logs indexados, Alertmanager con alertas críticas vía SMTP y webhook autenticado, OpenTelemetry Collector para trazas distribuidas.
* **Políticas de Datos**:
  - Ingesta programada en tiempo real de ChileCompra vía workers de Celery (`etl-worker` y `etl-beat`).
  - Segmentación de roles en PostgreSQL:
    * `market_insight_admin`: DDL, migraciones de Alembic y tareas de mantenimiento.
    * `market_insight_app`: CRUD operacional de la aplicación FastAPI.
    * `market_insight_readonly`: Consultas analíticas y scraping de métricas.
  - Resguardos automáticos diarios y retención planificada de backups.

---

## 3. Matriz Comparativa de Entornos

| Característica | Development | Testing | Staging | Production |
| :--- | :--- | :--- | :--- | :--- |
| **Comando Make** | `make dev-up` | `make test-env` | `make staging-up` | `make prod-up` |
| **Archivo Overlay** | `docker-compose.dev.yml` | `docker-compose.test.yml` | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| **Archivo de Variables** | `.env` / `docker/compose/.env.*` | `.env.test` / embebido | `.env.staging` (mandatorio) | `.env.prod` (mandatorio) |
| **Puertos Expuestos** | `127.0.0.1` (8000, 5173, etc.) | Ninguno (`ports: !reset []`) | Solo NGINX (`80`, `443`) | Solo NGINX (`80`, `443`) |
| **Proxy Reverso NGINX** | Opcional | Desactivado | Obligatorio (TLS) | Obligatorio (TLS) |
| **Formato de Logs** | Consola (`DEBUG`) | JSON (`INFO`) | JSON (`INFO`) | JSON (`INFO`) |
| **Rate Limiting** | Desactivado (`false`) | Desactivado (`false`) | Habilitado (`true`) | Habilitado (`true`) |
| **Herramientas Dev** | pgAdmin, RedisInsight | Ninguna | Ninguna | Ninguna |
| **ETL Scheduled Beat** | Opcional / Activo | Desactivado (`disabled`) | Activo controlado | Activo continuo |
| **Sentry / OTEL** | Desactivado | Desactivado | Habilitado (`staging`) | Habilitado (`production`) |
| **Políticas de Secretos** | Defaults locales seguros | Secretos fijos de test | Secretos únicos generados | Secretos de alta entropía |

---

## 4. Asignación de Recursos (Límites de CPU y Memoria)

Para evitar que una saturación en un servicio degrade los demás en entornos compartidos (staging y producción), se definen límites explícitos en los overlays:

| Servicio | Staging CPU | Staging RAM | Production CPU | Production RAM |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | 1.5 CPUs | 1.5 GB | 2.0 CPUs | 4.0 GB |
| **Redis** | 0.5 CPUs | 512 MB | 1.0 CPUs | 1.0 GB |
| **Backend API** | 1.5 CPUs | 1.5 GB | 2.0 CPUs | 2.0 GB |
| **NLP Worker** | 1.0 CPUs | 1.5 GB | 2.0 CPUs | 2.0 GB |
| **ETL Worker** | 1.0 CPUs | 1.5 GB | 2.0 CPUs | 2.0 GB |
| **Prometheus** | 0.5 CPUs | 1.0 GB | 1.0 CPUs | 2.0 GB |

---

## 5. Pipeline y Estrategia de Promoción

La promoción de código entre entornos sigue un flujo estricto de puertas de calidad (Quality Gates):

```text
Feature Branch
      │  (PR a main)
      ▼
Gate 1: Verificación en Testing
      ├── Linters y Formateo (ruff, eslint, prettier)
      ├── Typecheck estático (mypy / pyright, tsc)
      ├── Tests unitarios e integración (pytest, vitest)
      └── Validación de variables (.env templates)
      │
      ▼ (Merge a main)
Gate 2: Despliegue a Staging
      ├── Build de imágenes Docker multi-stage
      ├── Ejecución de migraciones: `alembic upgrade head`
      ├── Smoke tests automatizados (`/health/live`, `/health/ready`)
      └── Verificación de telemetría y alertas
      │
      ▼ (Aprobación manual de Release / Tag vX.Y.Z)
Gate 3: Despliegue a Producción
      ├── Snapshot / Backup preventivo de PostgreSQL
      ├── Ejecución de migraciones en modo transacción
      ├── Despliegue blue-green o rolling restart de contenedores
      ├── Smoke tests perimetrales sobre HTTPS
      └── Monitoreo intensivo de logs y tasas de error (SLO)
```

### Plan de Rollback Inmediato
Si tras la promoción a Staging o Producción los smoke tests fallan o la tasa de error 5xx supera el 1%:
1. Revertir el tráfico o restaurar el tag anterior de la imagen Docker (`make prod-up` con versión previa).
2. Si hubo migración de base de datos incompatible: ejecutar rollback de migración `alembic downgrade -1` utilizando el backup previo si hubo alteración destructiva de datos.
3. Notificar al canal de incidentes y registrar post-mortem operacional.

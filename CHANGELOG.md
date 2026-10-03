# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Soporte para alertas proactivas vía webhooks y mensajería en tiempo real.
- Integración con modelos locales vLLM para inferencia de bajo costo.
- Módulo de análisis predictivo de precios unitarios y colusión en licitaciones públicas.

---

## [1.0.0] - 2026-09-22

### Added
- **Despliegue y Operaciones (Fase 10)**:
  - Arquitectura multi-stage Docker para producción (`Dockerfile.prod`, `Dockerfile.worker.prod`) y NGINX perimetral.
  - Reverse Proxy NGINX con soporte SSE streaming para IA, compresión gzip y rate limiting.
  - Configuración TLS/HTTPS segura (TLSv1.2/1.3, ciphers modernos, HSTS preload) y scripts de automatización Let's Encrypt (`renew-certificates.sh`).
  - Estrategia de DNS y dominio unificado `https://mercadoinsight.cl`.
  - Pipelines CI/CD en GitHub Actions (`backend.yml`, `frontend.yml`, `security.yml`, `deploy.yml`) con publicación en GHCR (`ghcr.io/ernestostarck/market-insight`).
  - Escaneo de seguridad de contenedores con Trivy, generación de reportes SARIF y auditorías de dependencias (`bandit`, `pip-audit`, `npm audit`).
  - Estrategia y scripts de respaldo y recuperación ante desastres (`backup.py`, `restore.py`, `DISASTER_RECOVERY.md`).
- **Asistente IA y RAG (Fase 9)**:
  - Agente conversacional streaming SSE con soporte para Google Gemini y modelos alternativos.
  - Orquestación de contexto enriquecido mediante búsqueda híbrida en la base de conocimiento y base de datos relacional.
  - Sistema de trazabilidad, feedback de usuarios (pulgar arriba/abajo) y evaluación de respuestas.
- **Frontend SPA (Fase 8)**:
  - Interfaz web interactiva construida con React 18, TypeScript, TailwindCSS y Vite.
  - Vistas completas para Licitaciones, Adjudicaciones, Órdenes de Compra, Organismos, Proveedores, Análisis de Mercado y Chat IA.
  - Manejo de estado con React Query y Zustand, feedback visual accesible y pruebas E2E con Playwright.
- **Observabilidad y Telemetría (Fase 7)**:
  - Métricas con Prometheus y dashboards en Grafana para rendimiento, calidad de datos, SLIs/SLOs y Celery workers.
  - Trazas distribuidas con OpenTelemetry y captura de excepciones enriquecida con Sentry.
  - Registro estructurado en JSON y almacenamiento de logs en Grafana Loki.
- **Procesamiento de Lenguaje Natural (Fase 5 y 6)**:
  - Extracción y normalización de textos desde licitaciones y bases técnicas.
  - Generación y almacenamiento de embeddings vectoriales con pgvector.
  - Clasificación híbrida con reglas simbólicas y modelos supervisados, junto con un portal de revisión humana.
- **API REST FastAPI (Fase 4)**:
  - Endpoints REST `/api/v1` documentados con OpenAPI/Swagger para licitaciones, analítica y autenticación.
  - Autenticación JWT con rotación de tokens y control de acceso basado en roles (RBAC).

---

## [0.2.0] - 2026-09-01

### Added
- Modelos dimensionales Data Warehouse (`dw`) con soporte para Slowly Changing Dimensions Tipo 2 (SCD2).
- Vistas materializadas y particionamiento mensual para optimización analítica de licitaciones.
- Ingestión incremental automatizada con checkpoints y almacenamiento raw en MinIO.
- Búsqueda híbrida combinando Full-Text Search en PostgreSQL y similitud de cosenos vectorial.

---

## [0.1.0] - 2026-08-01

### Added
- Scaffold inicial del proyecto monorepo (`apps/backend`, `apps/frontend`, `packages/`).
- Cliente base de integración con las APIs públicas de ChileCompra y Mercado Público.
- Documentación inicial de arquitectura y roadmap estratégico.

### Changed
- Se formalizó la visión de MercadoInsight como plataforma de inteligencia de mercado por capas.

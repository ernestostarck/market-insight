# Roadmap

## Fase 0 - Arquitectura

- Definir la estructura del repositorio.
- Dockerizar backend, frontend y worker.
- Configuracion centralizada.
- CI/CD inicial.
- Documentacion base.

## Fase 1 - ChileCompra SDK

- Cliente reutilizable.
- Endpoints reales.
- Reintentos y rate limit.
- Normalizacion de respuestas.

## Fase 2 - ETL

- Extraccion incremental.
- Transformacion.
- Normalizacion.
- Enriquecimiento.
- Carga.

## Fase 3 - Base de datos

- Esquema relacional.
- Migrations con Alembic.
- pgvector y PostGIS.

## Fase 4 - API

- Recursos internos.
- Seguridad.
- Paginacion.
- Exportaciones.

## Fase 5 - NLP & Knowledge Layer

- Preprocessing lingüístico y consolidación de documentos.
- Taxonomía versionada de 3 niveles y diccionario semántico de dominio.
- Motor de reglas determinista y embeddings densos multilingües con pgvector (HNSW).
- Búsqueda semántica e híbrida (Reciprocal Rank Fusion).
- Extracción de entidades nombradas (NER) y extracción de productos técnicos.
- Clasificación supervisada, Gold Dataset y decisión híbrida.
- Relevancia de mercado y scoring de confianza.
- Cola priorizada de revisión humana (Human-in-the-loop) con retroalimentación.
- Procesamiento asíncrono con Celery worker (`nlp-worker`) y Redis.
- API REST unificada en `/api/v1/ai` con esquemas Pydantic y OpenAPI.
- MLOps: versionado inmutable, rollback automático, experimentos en MLflow y validación de regresión.
- Observabilidad: telemetría Prometheus, dashboards Grafana y detección de Data Drift (KL divergence).
- Validación end-to-end sobre datos reales de Mercado Público (ChileCompra) con F1 Macro 90.5% y latencia < 3ms (Completada al 100%).

## Fase 6 - Dashboard & Analytics

- KPIs de mercado y licitaciones.
- Gráficos ejecutivos de series temporales y distribución.
- Filtros por organismo, proveedor y categoría taxonómica.
- Mapas geográficos y visualización territorial.

## Fase 7 - Alertas & Suscripciones

- Reglas de alerta temprana.
- Notificaciones y suscripciones por categoría de interés.

## Fase 8 - RAG & Asistente Conversacional

- Búsqueda semántica aumentada y resumen de bases de licitación.
- Asistente conversacional de inteligencia de compras públicas.

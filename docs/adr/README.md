# Architecture Decision Records (ADR) — MercadoInsight

Este directorio recopila los registros de decisiones arquitectónicas de **MercadoInsight**, documentando el contexto, las alternativas evaluadas y las consecuencias técnicas de cada elección estructural del sistema.

---

## Índice de ADRs

| ID | Título | Área | Estado | Fecha |
| :---: | :--- | :--- | :---: | :---: |
| **[ADR-001](ADR-001-use-postgresql.md)** | Uso de PostgreSQL 17 como Motor Principal de Base de Datos | Base de Datos | Aceptado | 2026-08-15 |
| **[ADR-002](ADR-002-use-pgvector.md)** | Uso de pgvector para Almacenamiento e Indexación de Embeddings | IA / Vectorial | Aceptado | 2026-08-20 |
| **[ADR-003](ADR-003-use-fastapi.md)** | Uso de FastAPI para la Capa de API Backend | Backend / API | Aceptado | 2026-08-25 |
| **[ADR-004](ADR-004-hybrid-search.md)** | Adopción de Búsqueda Híbrida con Reciprocal Rank Fusion (RRF) | Búsqueda / NLP | Aceptado | 2026-08-28 |
| **[ADR-005](ADR-005-llm-gateway.md)** | Desacoplamiento de Proveedores LLM mediante Interfaz LLMGateway | IA / RAG | Aceptado | 2026-09-02 |
| **[ADR-006](ADR-006-react-frontend.md)** | Uso de React 18, TypeScript y Tailwind CSS en el Frontend | Frontend / UI | Aceptado | 2026-09-05 |
| **[ADR-007](ADR-007-docker-deployment.md)** | Despliegue Basado en Contenedores Docker y Docker Compose v2 | Infraestructura | Aceptado | 2026-09-10 |
| **[ADR-008](ADR-008-redis-broker-cache.md)** | Uso de Redis como Broker de Celery y Capa de Caché | Backend / Colas | Aceptado | 2026-09-12 |
| **[ADR-009](ADR-009-minio-object-storage.md)** | Uso de MinIO como Almacén de Objetos S3 Compatible | Almacenamiento | Aceptado | 2026-09-14 |
| **[ADR-010](ADR-010-hybrid-rag-strategy.md)** | Estrategia de RAG Híbrido con Clasificación Determinística de Intención | IA / RAG | Aceptado | 2026-09-16 |
| **[ADR-011](ADR-011-observability-stack.md)** | Adopción de la Pila Prometheus, Grafana, Loki y Sentry | Observabilidad | Aceptado | 2026-09-18 |
| **[ADR-012](ADR-012-github-actions-cicd.md)** | Adopción de GitHub Actions y GHCR para Pipelines de CI/CD | DevOps / CI/CD | Aceptado | 2026-09-19 |
| **[ADR-013](ADR-013-two-tier-network-architecture.md)** | Aislamiento de Red en Dos Niveles (Public-Net y Private-Net) | Seguridad / Red | Aceptado | 2026-09-20 |
| **[ADR-014](ADR-014-backup-manifest-sha256.md)** | Estrategia de Respaldos Criptográficamente Verificados con Manifiesto SHA-256 | Resiliencia / DR | Aceptado | 2026-09-21 |

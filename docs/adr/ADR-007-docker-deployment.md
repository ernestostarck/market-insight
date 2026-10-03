# ADR-007: Despliegue Basado en Contenedores Docker y Docker Compose v2

- **Status**: Aceptado
- **Fecha**: 2026-09-10
- **Decisores**: Equipo de DevOps e Infraestructura

---

## Contexto
La plataforma involucra múltiples servicios heterogéneos: backend FastAPI, frontend NGINX, base de datos PostgreSQL con extensiones compiladas (`pgvector`), broker Redis, almacén de objetos MinIO, workers Celery y la pila de observabilidad (Prometheus, Grafana, Loki). Es indispensable garantizar paridad estricta entre entornos de desarrollo, staging y producción.

## Decisión
Empaquetar todos los servicios mediante **imágenes Docker con compilación multi-stage** (`Dockerfile.prod`) y orquestar los entornos productivos y de staging mediante **Docker Compose v2** (`docker-compose.prod.yml`, `docker-compose.staging.yml`).

## Alternativas Consideradas
1. **Instalación Directa en el Host (Bare-Metal / Systemd)**: Menor overhead de virtualización, pero pesadilla de mantenimiento de versiones de Python, Node, librerías compartidas y colisiones de dependencias del sistema operativo.
2. **Kubernetes (K8s)**: Máxima capacidad de orquestación y escalado dinámico horizontal, pero introduce una complejidad operativa y costo de infraestructura desproporcionados para la fase actual de lanzamiento.

## Consecuencias
- **Positivas**:
  - **Reproducibilidad Total**: Garantía absoluta de que el código probado en CI/CD corre en el mismo entorno exacto en Producción.
  - **Imágenes Ligeras**: Los builds multi-stage reducen las imágenes de backend y frontend a menos de 150 MB al descartar compiladores y herramientas de desarrollo.
  - **Simplicidad Operativa**: Comandos estándar `docker compose up -d` y `docker compose pull` para despliegues y rollback.
- **Negativas**:
  - Requiere monitorear el uso de almacenamiento de volúmenes persistentes y podar periódicamente imágenes Docker obsoletas (`docker image prune`).

# Arquitectura de Infraestructura — Docker, NGINX & Redes

Este documento detalla la topología de infraestructura de **MercadoInsight**, los contenedores Docker, la configuración del proxy inverso NGINX y el esquema de aislamiento de red.

---

## 1. Topología de Red en Dos Niveles

Para garantizar máxima seguridad, el sistema opera con dos redes bridge independientes:

```text
                             INTERNET
                                │
                        [ Puertos 80/443 ]
                                ▼
                       ┌─────────────────┐
                       │  NGINX Ingress  │ (SSL Termination, Rate Limit, WAF)
                       └────────┬────────┘
                                │
                        RED PÚBLICA (public-net)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
        ┌─────────────────┐           ┌─────────────────┐
        │  Frontend SPA   │           │ FastAPI Backend │
        │   (Nginx est.)  │           │   (Uvicorn)     │
        └─────────────────┘           └────────┬────────┘
                                               │
                                       RED PRIVADA (private-net)
                                               │
        ┌──────────────┬──────────────┬────────┴─────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼              ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ PostgreSQL │ │   Redis    │ │   MinIO    │ │   Celery   │ │ Prometheus │ │    Loki    │
 │ (pgvector) │ │  (Cache)   │ │  (Storage) │ │  Workers   │ │ (Métricas) │ │   (Logs)   │
 └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘
```

### 1.1 Red Pública (`public-net`)
- **Propósito**: Canalizar tráfico exterior exclusivamente hacia el proxy inverso.
- **Servicios Miembros**:
  - `nginx`: Expone puertos `80/tcp` (HTTP -> HTTPS redirect) y `443/tcp` (TLSv1.2/1.3).
  - `frontend`: Servidor de archivos estáticos compilados de React.
  - `backend`: Recibe peticiones enrutadas bajo `/api/*`.

### 1.2 Red Privada (`private-net`)
- **Propósito**: Aislamiento estricto de motores de almacenamiento, procesamiento y telemetría.
- **Servicios Miembros**:
  - `postgres`: Base de datos principal. **Cero puertos publicados al host.**
  - `redis`: Broker y caché. **Cero puertos publicados al host.**
  - `minio`: Almacén de objetos y respaldos. **Cero puertos publicados al host.**
  - `celery_worker`: Tareas asíncronas de NLP y ETL.
  - `prometheus`, `loki`, `promtail`: Infraestructura de observabilidad.
- **Servicios Puente**: `backend`, `grafana` y `alertmanager` pertenecen a ambas redes para permitir acceso a la API y dashboards administrativos.

---

## 2. NGINX Reverse Proxy y Seguridad

Configurado con directivas de alto rendimiento y endurecimiento (*hardening*):
- **Protocolos Cifrados**: TLSv1.2 y TLSv1.3 con suites de cifrado modernas (ECDHE-ECDSA-AES128-GCM-SHA256, ECDHE-RSA-AES256-GCM-SHA384).
- **HSTS (HTTP Strict Transport Security)**: `max-age=31536000; includeSubDomains; preload`.
- **Cabeceras de Protección**:
  - `Content-Security-Policy`: Restringe scripts y recursos externos.
  - `X-Frame-Options: DENY`: Prevención de Clickjacking.
  - `X-Content-Type-Options: nosniff`: Prevención de MIME-sniffing.
  - `Permissions-Policy`: Deshabilita acceso no autorizado a cámara, micrófono y geolocalización.
- **Rate Limiting**:
  - Zona de API: `10r/s` con ráfaga (*burst*) de 20 peticiones.
  - Zona de Auth: `5r/m` con ráfaga de 5 peticiones para mitigar ataques de fuerza bruta.
- **Compresión Gzip / Brotli**: Habilitada para respuestas JSON y assets estáticos mayores a 1 KB.

---

## 3. Estrategia de Contenedores y Recursos

- **Multi-Stage Builds**: Imágenes Docker optimizadas basadas en `python:3.14-slim` y `node:20-alpine`, descartando compiladores y librerías de build tras la compilación.
- **Límites de Recursos (Resource Quotas)**:
  - `postgres`: 4 CPU, 4 GB RAM (shared_buffers 1GB, work_mem 32MB).
  - `backend`: 2 CPU, 2 GB RAM (4 workers Uvicorn por contenedor).
  - `celery_worker`: 2 CPU, 2 GB RAM (concurrencia de 4 procesos worker).
  - `redis`: 1 CPU, 1 GB RAM (política de desalojo `volatile-lru`).
- **Healthchecks Nativos**: Cada contenedor define una directiva `healthcheck` con `interval: 15s`, `timeout: 5s`, `retries: 3` y `start_period: 30s`.

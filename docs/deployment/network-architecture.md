# Arquitectura y Segmentación de Red — MercadoInsight

Este documento detalla la topología de red multicapa, el aislamiento perimetral y las directrices de seguridad de comunicaciones para **MercadoInsight** implementadas en Docker Compose (Fase 10.20).

---

## 1. Topología de Red en Dos Niveles (Two-Tier Network Architecture)

El despliegue productivo y de staging implementa una estricta segmentación entre la zona pública (DMZ perimetral) y la zona privada de persistencia y procesamiento:

```text
                            INTERNET
                                │
                                ▼ [Puertos 80/443]
                       ┌─────────────────┐
                       │  NGINX Reverse  │
                       │      Proxy      │
                       └────────┬────────┘
                                │
══════════════════════════ PUBLIC NETWORK ══════════════════════════
               │                                │
               ▼                                ▼
       ┌───────────────┐                ┌───────────────┐
       │ Frontend SPA  │                │  Backend API  │
       │ (dist NGINX)  │                │   (FastAPI)   │
       └───────────────┘                └───────┬───────┘
                                                │
═════════════════════════ PRIVATE NETWORK ══════╪═══════════════════
                                                │
         ┌──────────────────┬───────────────────┼──────────────────┐
         ▼                  ▼                   ▼                  ▼
┌─────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│   PostgreSQL    │ │  Redis Cache   │ │  MinIO Object  │ │ Celery Workers │
│  (DB Relacional)│ │  & Broker      │ │    Storage     │ │  (NLP & ETL)   │
└─────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
         │                  │                   │                  │
         └──────────────────┴─────────┬─────────┴──────────────────┘
                                      ▼
                             ┌────────────────┐
                             │   Prometheus   │
                             │  & Telemetría  │
                             └────────────────┘
```

---

## 2. Matriz de Pertenencia a Redes

| Servicio | `public-net` | `private-net` | Justificación Técnica |
| :--- | :---: | :---: | :--- |
| **`nginx`** | ✅ | ❌ | Único punto de entrada que escucha en la interfaz pública del host (`0.0.0.0:80/443`). No tiene acceso directo a la base de datos ni a Redis. |
| **`frontend`** | ✅ | ❌ | Servidor web NGINX estático para los assets empaquetados de React. Solo es consultado por NGINX perimetral. |
| **`backend`** | ✅ | ✅ | **Puente (Bridge)**: Recibe peticiones HTTP desde NGINX en `public-net` y consulta bases de datos, caché y MinIO en `private-net`. |
| **`postgres`** | ❌ | ✅ | **Estrictamente privado**: Solo accesible para `backend`, workers y `postgres-exporter`. |
| **`redis`** | ❌ | ✅ | **Estrictamente privado**: Solo accesible para `backend`, workers y `redis-exporter`. Protegido adicionalmente por contraseña. |
| **`minio`** | ❌ | ✅ | **Estrictamente privado**: Almacenamiento de documentos brutos, accesible solo internamente. |
| **`nlp-worker`** | ❌ | ✅ | Procesa tareas asíncronas de NLP consultando Postgres y Redis. Sin interfaz pública. |
| **`etl-worker`** | ❌ | ✅ | Ejecuta extracciones programadas y escribe en Postgres/MinIO. Sin interfaz pública. |
| **`prometheus`** | ❌ | ✅ | Scrapea `/metrics` internamente en la red privada. |
| **`grafana`** | ✅ | ✅ | Proxied por NGINX (`/grafana/`) con Basic Auth, consulta Prometheus/Loki en la red privada. |
| **`alertmanager`** | ✅ | ✅ | Proxied por NGINX (`/alertmanager/`), recibe alertas de Prometheus en la red privada. |
| **`loki` / `promtail`** | ❌ | ✅ | Recolección e indexación interna de logs de contenedores. |

---

## 3. Principio de Mínima Exposición de Puertos

En los entornos productivos (`docker-compose.prod.yml`) y de staging (`docker-compose.staging.yml`):

1. **Reset Obligatorio de Puertos**:
   Todos los servicios heredados del archivo base `docker-compose.yml` que tenían puertos mapeados a `127.0.0.1` en desarrollo se anulan explícitamente mediante la directiva `ports: !reset []`.
2. **Imposibilidad de Acceso Directo**:
   Aun si un atacante intenta conectarse a los puertos 5432 (PostgreSQL), 6379 (Redis) o 9000 (MinIO) en la IP pública del servidor, el firewall del host y Docker descartarán los paquetes porque dichos puertos **no están abiertos en el sistema operativo host**.
3. **Aislamiento Contenedor a Contenedor**:
   Un eventual compromiso del contenedor `frontend` no permite alcanzar la base de datos `postgres` ni `redis` porque no comparten la red `private-net`.

---

## 4. Configuración en Docker Compose

```yaml
networks:
  public-net:
    name: mercadoinsight_public_net
    driver: bridge
  private-net:
    name: mercadoinsight_private_net
    driver: bridge
```

### Verificación en el Servidor
```bash
# Inspeccionar servicios en la red pública
docker network inspect mercadoinsight_public_net

# Inspeccionar servicios en la red privada
docker network inspect mercadoinsight_private_net
```

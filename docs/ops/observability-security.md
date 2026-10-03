# Arquitectura de Seguridad para la Observabilidad — MercadoInsight

Este documento describe las políticas, configuraciones y controles implementados para garantizar la **seguridad del stack de observabilidad** y prevenir la exposición indebida de servicios internos, métricas o bases de datos en **MercadoInsight**.

---

## 1. Perímetro de Red y Separación de Servicios

Para evitar vectores de ataque y fugas de información, la arquitectura distingue estrictamente entre **servicios públicos** y **servicios internos**:

### 1.1 Servicios Públicos (Exposición Externa)
- **Nginx Gateway (`:80`)**: Único punto de entrada perimetral. Enruta el tráfico hacia el frontend (`/`) y hacia la API REST (`/api/v1/`).
- **Frontend SPA (`:5173`)**: Acceso web para usuarios autenticados.

### 1.2 Servicios Internos (Aislamiento Loopback `127.0.0.1`)
Todos los demás servicios y herramientas de soporte están enlazados exclusivamente a la interfaz local `127.0.0.1` en el archivo `docker-compose.yml`, impidiendo cualquier conexión directa desde interfaces de red externas o internet:

| Servicio | Puerto Interno | Enlace Host | Propósito | Justificación de Seguridad |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `5432` | `127.0.0.1:5432` | Base de datos relacional OLTP | Previene ataques de fuerza bruta y escaneo de puertos. |
| **Redis** | `6379` | `127.0.0.1:6379` | Caché, rate limiting y colas Celery | Protege contra ejecución remota o robo de tokens de sesión. |
| **MinIO (S3 API)** | `9000` | `127.0.0.1:9000` | Almacenamiento de objetos S3 | Acceso directo a documentos restringido a la red interna. |
| **MinIO Console** | `9001` | `127.0.0.1:9001` | Consola administrativa MinIO | Solo accesible por desarrolladores/administradores locales. |
| **FastAPI Backend** | `8000` | `127.0.0.1:8000` | API application server | El tráfico externo debe pasar obligatoriamente por Nginx. |
| **Prometheus** | `9090` | `127.0.0.1:9090` | Motor de métricas TSDB | Protege reglas operacionales y metadata de infraestructura. |
| **Alertmanager** | `9093` | `127.0.0.1:9093` | Gestor y enrutador de alertas | Impide silenciamiento no autorizado de alarmas críticas. |
| **Grafana** | `3000` | `127.0.0.1:3000` | Dashboards visuales | Autenticación reforzada; accesible vía túnel VPN o localhost. |
| **Loki** | `3100` | `127.0.0.1:3100` | Agregador de logs distribuidos | Previene exfiltración de registros y trazas de auditoría. |
| **cAdvisor** | `8080` | `127.0.0.1:8088` | Métricas de contenedores Docker | Exposición de nombres y consumos de contenedor mitigada. |
| **Postgres Exporter** | `9187` | `127.0.0.1:9187` | Prometheus exporter de PG | Aislado para scraping exclusivo por Prometheus. |
| **Redis Exporter** | `9121` | `127.0.0.1:9121` | Prometheus exporter de Redis | Aislado para scraping exclusivo por Prometheus. |
| **pgAdmin** | `80` | `127.0.0.1:5050` | Interfaz gráfica de PostgreSQL | Herramienta administrativa no expuesta a internet. |
| **RedisInsight** | `5540` | `127.0.0.1:5540` | Interfaz gráfica de Redis | Herramienta analítica interna en loopback. |

---

## 2. Protección del Endpoint `/metrics`

Las métricas internas exponen información sensible sobre tasas de error, nombres de rutas, identificadores de tablas y tiempos de procesamiento. Se han aplicado dos capas de defensa:

### 2.1 Bloqueo en Nginx Gateway
La configuración del proxy perimetral (`docker/nginx/conf.d/default.conf`) bloquea explícitamente cualquier acceso público a `/metrics`:
```nginx
location = /metrics {
    return 403 "Forbidden\n";
}
```

### 2.2 Autenticación de Scraping en FastAPI (`METRICS_AUTH_TOKEN`)
En el backend, el middleware de métricas (`MetricsMiddleware`) valida la presencia de un token de autenticación cuando la variable de entorno `METRICS_AUTH_TOKEN` está configurada:
- **Cabeceras Aceptadas**:
  - `Authorization: Bearer <METRICS_AUTH_TOKEN>`
  - `X-Metrics-Token: <METRICS_AUTH_TOKEN>`
- **Comportamiento si no coincide o falta**: Respuesta HTTP `401 Unauthorized`.
- **Comportamiento en Desarrollo/Tests**: Si `METRICS_AUTH_TOKEN` no está configurado (valor `None`), se permite el scraping abierto dentro de la red privada Docker para facilitar el desarrollo local sin fricción.

---

## 3. Endurecimiento de Grafana

La configuración en `docker/compose/.env.grafana` aplica los siguientes parámetros de seguridad:
- `GF_AUTH_ANONYMOUS_ENABLED=false`: Prohíbe cualquier acceso o visualización anónima de tableros.
- `GF_USERS_ALLOW_SIGN_UP=false`: Deshabilita el auto-registro público de nuevos usuarios.
- `GF_USERS_ALLOW_ORG_CREATE=false`: Impide la creación indiscriminada de organizaciones por usuarios estándar.
- `GF_AUTH_BASIC_ENABLED=true`: Autenticación con contraseña fuerte administrada centralmente.
- `GF_SECURITY_ADMIN_PASSWORD`: Forzado a contraseña compleja personalizable mediante variables de entorno (no usa contraseñas predecibles).
- `GF_SECURITY_DISABLE_GRAVATAR=true`: Evita fugas de emails de usuarios a servicios externos de avatar.

---

## 4. Auditoría y Gestión de Credenciales

1. **Credenciales de Exportadores**:
   - `postgres-exporter` y `redis-exporter` utilizan credenciales específicas inyectadas mediante variables de entorno en tiempo de ejecución.
   - En entornos de producción, se recomienda crear usuarios de PostgreSQL con privilegios mínimos de solo lectura (`pg_monitor` role).
2. **Ciclo de Vida de Prometheus**:
   - La opción `--web.enable-lifecycle` está activa en Prometheus para recargar configuraciones en caliente (`POST /-/reload`), pero al estar enlazado a `127.0.0.1` o consumido desde la red Docker interna `mercadoinsight`, no puede ser invocada por actores externos.
3. **Control de Repositorio**:
   - Ningún secreto ni archivo `.env` de producción se almacena en el control de versiones. Todos los archivos `.env` y `.env.*` están protegidos en `.gitignore`.

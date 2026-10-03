# Gestión de Secretos — MercadoInsight

Este documento detalla la estrategia de gestión de secretos, la evaluación técnica de proveedores de secretos (Docker Secrets, HashiCorp Vault y Cloud Secret Managers), los procedimientos operativos de rotación de credenciales y los mecanismos de prevención contra fugas de información sensible en **MercadoInsight**.

---

## 1. Estrategia de Secretos por Entorno

Para equilibrar la agilidad en desarrollo con la máxima seguridad en producción, se aplican tres niveles progresivos:

| Entorno | Estrategia de Inyección | Nivel de Confidencialidad | Almacenamiento |
| :--- | :--- | :--- | :--- |
| **Development** | Archivo `.env` local y `docker/compose/.env.*` (ignorados por Git). | Bajo: valores por defecto conocidos de desarrollo (`market_insight_dev`). | Sistema de archivos local del desarrollador. |
| **Staging** | Variables de entorno inyectadas mediante `--env-file .env.staging` (permisos `chmod 600`) o GitHub Actions Secrets. | Alto: contraseñas aleatorias únicas de 24+ bytes. No se comparten con producción. | Servidor de staging / Secret store de CI. |
| **Production** | Docker Secrets montados en memoria (`/run/secrets/*`), variables de entorno cifradas o Cloud Secret Manager. | Crítico: alta entropía (`openssl rand -hex 24`), rotación periódica. | Bóveda de secretos o Docker daemon con permisos restringidos. |

---

## 2. Evaluación de Tecnologías de Gestión de Secretos

MercadoInsight está diseñado bajo un **principio agnóstico de infraestructura**: la aplicación no contiene código propietario atado a un proveedor cloud específico. Los secretos se inyectan a través del estándar POSIX: variables de entorno o archivos de secretos montados en `/run/secrets/`.

### 2.1 Docker Secrets (Implementación Actual)
* **Cómo funciona**: Docker Swarm o Docker Compose v2 mapean variables seguras como archivos en `/run/secrets/<secret_name>` accesibles únicamente por el contenedor especificado.
* **Uso en el proyecto**: Utilizado en `docker-compose.prod.yml` y `docker-compose.staging.yml` para desacoplar credenciales críticas de Alertmanager (`alert_webhook_token`, `alert_smtp_password`).
* **Ventajas**: Nativo en Docker, no requiere infraestructura adicional, los secretos residen en memoria `tmpfs` y nunca se graban en capas de imagen.
* **Limitaciones**: Rotación manual de contenedores tras cambio de valor. Ideal para despliegues VPS y Docker Compose.

### 2.2 HashiCorp Vault
* **Cómo funciona**: Servidor centralizado que genera credenciales dinámicas con tiempo de vida (TTL), cifrado en tránsito/reposo y auditoría de accesos exhaustiva.
* **Cuándo adoptarlo**: En despliegues Kubernetes o multi-cloud donde se requiera emisión dinámica de credenciales de PostgreSQL con revocación automática por tiempo.
* **Patrón de integración agnóstico**: Un contenedor init (o Vault Agent Sidecar) descarga los secretos a un volumen `tmpfs` (`/run/secrets/vault`) antes de iniciar FastAPI, manteniendo el código de la aplicación inalterado.

### 2.3 Cloud Secret Managers (AWS, Azure, GCP)
* **Servicios**: AWS Secrets Manager / SSM Parameter Store, Azure Key Vault, Google Secret Manager.
* **Cuándo adoptarlo**: Cuando MercadoInsight se despliegue directamente en infraestructuras gestionadas por dichos proveedores (ej. AWS ECS Fargate, Azure Container Apps, Google Cloud Run).
* **Patrón de integración agnóstico**: El agente de ejecución del proveedor cloud inyecta los secretos como variables de entorno del contenedor en el momento del arranque (mediante IAM Roles / Workload Identity), garantizando cero código vendor en FastAPI.

---

## 3. Procedimientos Operativos de Rotación de Credenciales

Toda rotación debe documentarse y realizarse minimizando o eliminando el tiempo de inactividad (Zero-Downtime Rotation).

### 3.1 Rotación de `SECRET_KEY` (Firma de Sesión JWT)
> [!WARNING]
> La rotación de `SECRET_KEY` invalida inmediatamente todos los tokens JWT emitidos previamente. Los usuarios autenticados deberán volver a iniciar sesión.

1. **Generar nueva clave de 256 bits**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Actualizar archivo de entorno**:
   Editar `.env.prod` o el secret store con el nuevo valor.
3. **Reiniciar servicio API**:
   ```bash
   make prod-up
   ```
4. **Verificación**: Comprobar en `/health/ready` que la API levanta sin errores y validar login en `/api/v1/auth/login`.

---

### 3.2 Rotación de Contraseñas de Base de Datos (PostgreSQL)
Para evitar disrupciones en la ingesta ETL y en las consultas de usuarios, se rota un rol a la vez:

1. **Generar nueva contraseña**:
   ```bash
   openssl rand -hex 24
   ```
2. **Actualizar el rol en PostgreSQL en caliente**:
   Conectarse al contenedor de base de datos como administrador:
   ```bash
   docker exec -it $(docker compose ps -q postgres) psql -U market_insight -d market_insight
   ```
   Ejecutar la alteración de rol:
   ```sql
   ALTER USER market_insight_app WITH PASSWORD '<NUEVA_CONTRASENA>';
   ```
3. **Actualizar variable `MARKET_INSIGHT_APP_PASSWORD` y `DATABASE_URL`**:
   Reflejar la nueva contraseña en `.env.prod`.
4. **Reiniciar servicios consumidores**:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d backend nlp-worker etl-worker
   ```
5. **Verificar conexión**: Validar que los workers sigan consumiendo colas y `/health/ready` responda `healthy`.

---

### 3.3 Rotación de Contraseña de Redis (`REDIS_PASSWORD`)
1. **Generar nueva clave**:
   ```bash
   openssl rand -hex 24
   ```
2. **Actualizar configuración en Redis en caliente (opcional)**:
   ```bash
   docker exec -it $(docker compose ps -q redis) redis-cli -a "<PASSWORD_ACTUAL>" CONFIG SET requirepass "<NUEVA_CONTRASENA>"
   ```
3. **Actualizar `.env.prod`** con el nuevo `REDIS_PASSWORD` y la nueva `REDIS_URL`.
4. **Reiniciar los servicios dependientes**:
   ```bash
   make prod-up
   ```

---

### 3.4 Rotación de Credenciales de MinIO / S3
1. Generar nuevas credenciales de acceso para el servicio en la consola MinIO o mediante el comando `mc`:
   ```bash
   mc admin user add myminio <NUEVO_ACCESS_KEY> <NUEVO_SECRET_KEY>
   mc admin policy attach myminio readwrite --user <NUEVO_ACCESS_KEY>
   ```
2. Actualizar `MINIO_ACCESS_KEY` y `MINIO_SECRET_KEY` en `.env.prod`.
3. Reiniciar backend y workers.
4. Una vez validada la subida y lectura de documentos, deshabilitar o eliminar la clave antigua:
   ```bash
   mc admin user disable myminio <ANTIGUO_ACCESS_KEY>
   ```

---

### 3.5 Rotación de Ticket / API Key de ChileCompra
1. Solicitar o generar nuevo Ticket de acceso en la plataforma de Mercado Público.
2. Probar conectividad con el nuevo ticket usando curl o el script de prueba:
   ```bash
   curl -s "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?ticket=<NUEVO_TICKET>"
   ```
3. Reemplazar `CHILECOMPRA_API_KEY` en `.env.prod`.
4. Reiniciar el worker ETL:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d etl-worker etl-beat
   ```

---

### 3.6 Rotación de Tokens de Monitoreo (`ALERT_WEBHOOK_TOKEN` y `METRICS_AUTH_TOKEN`)
1. Generar nuevo token:
   ```bash
   openssl rand -hex 24
   ```
2. Actualizar en `.env.prod` tanto en `ALERT_WEBHOOK_TOKEN` como en la configuración de Alertmanager.
3. Desplegar los servicios:
   ```bash
   make prod-up
   ```
4. Probar webhook de alertas para verificar que no emite errores 401:
   ```bash
   curl -H "Authorization: Bearer <NUEVO_TOKEN>" http://127.0.0.1:8000/api/v1/monitoring/alerts/webhook
   ```

---

### 3.7 Renovación y Rotación de Certificados TLS (HTTPS)
* Los certificados en producción residen en `docker/nginx/certs/fullchain.pem` y `privkey.pem`.
* **Con Certbot / Let's Encrypt**:
  ```bash
  certbot certonly --webroot -w /var/www/certbot -d mercadoinsight.cl -d www.mercadoinsight.cl
  ```
* **Recarga de NGINX sin caída**:
  Tras renovar los archivos de certificado, recargar NGINX en caliente:
  ```bash
  docker compose exec nginx nginx -s reload
  ```

---

## 4. Prevención contra Fugas de Secretos

Para garantizar que los secretos nunca queden expuestos ni en código, ni en logs, ni en imágenes Docker, se implementan cuatro anillos de protección:

### 4.1 Anillo 1: Filtro de Logs y Enmascaramiento Dinámico
El módulo [`apps/backend/app/core/logging.py`](file:///c:/Users/artut/market-insight/apps/backend/app/core/logging.py) inspecciona todos los registros:
* Claves sensibles (`password`, `secret`, `token`, `authorization`, `api_key`, `ticket`) son sustituidas automáticamente por `***REDACTED***`.
* Expresiones regulares analizan cadenas de texto libre para enmascarar cabeceras `Bearer ...` y credenciales incrustadas en URLs (`scheme://user:pass@host`).

### 4.2 Anillo 2: Manejadores de Errores Seguros
El módulo [`apps/backend/app/core/exceptions.py`](file:///c:/Users/artut/market-insight/apps/backend/app/core/exceptions.py) captura excepciones no controladas:
* Errores 500 retornan un mensaje genérico `"An unexpected internal server error occurred."` junto al `request_id`.
* Los stack traces detallados se envían exclusivamente a logs internos y Sentry, impidiendo que clientes HTTP externos visualicen cadenas de conexión o variables internas.

### 4.3 Anillo 3: Blindaje de Docker Build Context (`.dockerignore`)
* Se han establecido archivos [`.dockerignore`](file:///c:/Users/artut/market-insight/.dockerignore) estrictos en raíz, backend y frontend.
* Archivos `.env*`, claves `.pem`/`.key`, certificados y bases de datos locales son excluidos del contexto de construcción, imposibilitando que queden embutidos en las capas de las imágenes Docker finales.

### 4.4 Anillo 4: Control de Versiones Git (`.gitignore`)
* Todos los patrones de variables reales (`.env`, `.env.*`) están ignorados por defecto, permitiendo únicamente el versionado de plantillas `.example`.
* El validador [`validate-env.py`](file:///c:/Users/artut/market-insight/infrastructure/scripts/validate-env.py) detecta e impide que se utilicen placeholders o secretos predeterminados en ambientes de staging o producción.

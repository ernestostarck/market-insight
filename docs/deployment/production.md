# Guía de Puesta en Producción — Production Setup

Esta guía detalla el procedimiento de despliegue, endurecimiento y operación del entorno de **Producción** de **MercadoInsight**.

---

## 1. Requisitos de Infraestructura Productiva

- **Servidor Dedicado / Instancia Cloud**:
  - Mínimo: 4 vCPU, 8 GB RAM, 80 GB SSD NVMe.
  - Recomendado: 8 vCPU, 16 GB RAM, 200 GB SSD NVMe.
- **Sistema Operativo**: Ubuntu 24.04 LTS o Debian 12 (con actualizaciones de seguridad al día).
- **Dominio y DNS**: Registro tipo A configurado apuntando a la IP pública del servidor (`mercadoinsight.cl` y `api.mercadoinsight.cl`).
- **Firewall (`ufw`)**: Únicamente puertos `22/tcp` (SSH), `80/tcp` (HTTP) y `443/tcp` (HTTPS) abiertos al exterior.

---

## 2. Preparación y Secretos

1. **Variables de Entorno**:
   Crear `.env.prod` protegiendo sus permisos (`chmod 600 .env.prod`):
   ```ini
   ENVIRONMENT=production
   DEBUG=False
   SECRET_KEY=<generar_con_openssl_rand_hex_32>
   APP_VERSION=1.0.0
   POSTGRES_USER=mercado_prod_user
   POSTGRES_PASSWORD=<password_alta_entropia>
   POSTGRES_DB=market_insight_prod
   DATABASE_URL=postgresql+asyncpg://mercado_prod_user:<password>@postgres:5432/market_insight_prod
   REDIS_URL=redis://redis:6379/0
   MINIO_ENDPOINT=minio:9000
   MINIO_ACCESS_KEY=<minio_prod_access_key>
   MINIO_SECRET_KEY=<minio_prod_secret_key>
   CORS_ORIGINS=["https://mercadoinsight.cl"]
   SENTRY_DSN=https://...
   OPENAI_API_KEY=sk-proj-...
   ```

2. **Certificados TLS**:
   Obtener certificados mediante Let's Encrypt / Certbot para `mercadoinsight.cl`:
   ```bash
   certbot certonly --standalone -d mercadoinsight.cl -d api.mercadoinsight.cl
   ```

---

## 3. Despliegue Paso a Paso

1. **Clonar e Inicializar**:
   ```bash
   git clone https://github.com/ernestostarck/market-insight.git /opt/market-insight
   cd /opt/market-insight
   git checkout tags/v1.0.0
   ```

2. **Descargar Imágenes Certificadas desde GHCR**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml pull
   ```

3. **Ejecutar Migraciones de Base de Datos**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend alembic upgrade head
   ```

4. **Levantar Servicios con Redes Aisladas**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml up -d --remove-orphans
   ```

5. **Auditoría de Seguridad Inmediata**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend python /opt/market-insight/infrastructure/scripts/security-audit.py
   ```

---

## 4. Verificación Post-Despliegue

Ejecutar las siguientes validaciones operacionales:
```bash
# 1. Healthcheck general
curl -f https://mercadoinsight.cl/health/ready

# 2. Verificación de cabeceras de seguridad
curl -I https://mercadoinsight.cl/api/v1/system/status

# 3. Inspección de puertos publicados en host (sólo NGINX debe responder)
netstat -tulpn | grep LISTEN
```

---

## 5. Mantenimiento y Backups

Configurar cron para respaldo automático diario a las 02:00 UTC:
```bash
0 2 * * * root /usr/bin/python3 /opt/market-insight/infrastructure/scripts/backup.py --type full --output-dir /var/backups/market-insight --retention-days 14 >> /var/log/market-insight-backup.log 2>&1
```

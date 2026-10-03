# Plan de Recuperación ante Desastres (Disaster Recovery) — MercadoInsight

Este documento establece el protocolo operacional, responsabilidades y procedimientos técnicos para restaurar la plataforma **MercadoInsight** ante incidentes catastróficos, corrupción de datos o fallas críticas de infraestructura (Fase 10.15).

---

## 1. Objetivos de Continuidad Operacional

* **RTO (Recovery Time Objective)**: **$\le 1$ hora** desde la declaración formal de contingencia hasta el restablecimiento del servicio con tráfico de usuarios.
* **RPO (Recovery Point Objective)**:
  * **$\le 24$ horas** utilizando el último respaldo consolidado diario.
  * **$\le 1$ hora** en entornos con archivado continuo de Write-Ahead Logging (WAL/PITR).

---

## 2. Roles y Cadena de Comunicación en Contingencia

| Rol | Responsabilidad |
| :--- | :--- |
| **Comandante de Incidente (IC)** | Declara la contingencia, coordina las acciones, aprueba la conmutación al entorno de recuperación y emite los comunicados internos. |
| **Ingeniero de Infraestructura / SRE** | Ejecuta el aprovisionamiento del host, verificación de certificados TLS, y orquestación de Docker / NGINX. |
| **Ingeniero de Datos / Backend** | Valida el manifiesto criptográfico de backup, ejecuta la restauración de PostgreSQL y MinIO, y valida las migraciones de Alembic. |
| **QA / Frontend Lead** | Ejecuta el checklist de integridad funcional, prueba los flujos del frontend SPA y verifica los healthchecks de la API. |

---

## 3. Escenarios de Desastre y Protocolos de Respuesta

### Escenario A: Corrupción o Borrado Accidental de la Base de Datos PostgreSQL

1. **Aislamiento Inmediato**:
   Detener los contenedores backend y worker para evitar que escrituras corruptas se propaguen:
   ```bash
   docker compose stop backend worker
   ```
2. **Seleccionar el Respaldo Más Reciente**:
   Localizar el último directorio de respaldo en `/var/backups/mercadoinsight` o descargarlo desde el bucket de almacenamiento secundario inmutable.
3. **Verificación Criptográfica del Manifiesto**:
   Ejecutar la verificación estricta de checksum SHA-256 para asegurar que el dump no esté corrupto ni alterado:
   ```bash
   python infrastructure/scripts/restore.py --manifest /var/backups/mercadoinsight/manifest.json --verify-only
   ```
4. **Restaurar el Esquema y Datos**:
   ```bash
   python infrastructure/scripts/restore.py --manifest /var/backups/mercadoinsight/manifest.json
   ```
5. **Verificar Migraciones de Alembic**:
   ```bash
   docker compose run --rm backend alembic current
   ```
6. **Reanudar Servicios y Validar**:
   ```bash
   docker compose start backend worker
   curl -f http://localhost:8000/health/ready
   ```

---

### Escenario B: Falla Catastrófica del Servidor o Pérdida de Host

1. **Aprovisionar Nuevo Servidor**:
   Instanciar una máquina virtual o servidor bare-metal con Ubuntu 24.04 LTS o Debian 12 con Docker y Docker Compose instalados.
2. **Clonar Repositorio y Configurar Variables**:
   ```bash
   git clone https://github.com/ernestostarck/market-insight.git
   cd market-insight
   # Restaurar el archivo cifrado de producción o aplicar secrets
   cp /secure/keys/.env.prod .env.prod
   ```
3. **Descargar Último Backup y Manifiesto**:
   Descargar el archivo `.dump` y `manifest.json` desde el almacenamiento secundario externo en la nube.
4. **Levantar Servicios Base**:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d postgres redis minio
   ```
5. **Restaurar Base de Datos y Objetos**:
   ```bash
   python infrastructure/scripts/restore.py --manifest /path/to/manifest.json
   ```
6. **Levantar Stack Completo**:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d
   ```
7. **Conmutación de DNS**:
   Actualizar el registro A de `mercadoinsight.cl` hacia la nueva IP pública del servidor si hubo cambio de dirección IP.

---

### Escenario C: Compromiso de Seguridad o Fuga de Credenciales

1. **Rotación Inmediata de Secretos**:
   - Generar un nuevo `SECRET_KEY` aleatorio (mínimo 64 caracteres hex): `openssl rand -hex 32`.
   - Rotar contraseñas de `POSTGRES_PASSWORD`, credenciales de Redis y MinIO.
   - Rotar tokens de servicio de ChileCompra / Mercado Público.
2. **Invalidación de Sesiones**:
   Al modificar `SECRET_KEY`, todos los JWTs emitidos previamente quedan automáticamente invalidados por la capa de autenticación.
3. **Reinicio Forzado de Contenedores**:
   ```bash
   docker compose --env-file .env.prod up -d --force-recreate
   ```

---

## 4. Entorno Aislado de Recuperación (Recovery Sandbox)

Para realizar pruebas de restauración o auditorías forenses sin tocar el entorno productivo:

```bash
# 1. Crear red y contenedor aislado temporal
docker run -d --name pg-recovery-sandbox \
  -e POSTGRES_DB=market_insight_recovery \
  -e POSTGRES_USER=recovery_user \
  -e POSTGRES_PASSWORD=temporary_recovery_pwd \
  -p 5439:5432 \
  postgres:16-alpine

# 2. Restaurar el dump en el sandbox
python infrastructure/scripts/restore.py \
  --manifest /var/backups/mercadoinsight/manifest.json \
  --target-db-url "postgresql://recovery_user:temporary_recovery_pwd@localhost:5439/market_insight_recovery"

# 3. Validar consistencia y destruir el sandbox
docker stop pg-recovery-sandbox && docker rm pg-recovery-sandbox
```

---

## 5. Checklist de Verificación Post-Recuperación

Antes de desviar el tráfico de producción a la instancia recuperada:

- [ ] **Hash SHA-256 verificado**: El archivo de respaldo coincide exactamente con el manifiesto inmutable.
- [ ] **Tablas relacionales presentes**: `licitaciones`, `licitacion_items`, `organismos`, `proveedores`, `users`, `etl_runs`.
- [ ] **Vectores de conocimiento**: Los índices vectoriales HNSW en `knowledge.embeddings` responden consultas de similitud.
- [ ] **Revisión Alembic**: `alembic current` coincide con la cabeza esperada del release.
- [ ] **Health Probes API**:
  - `GET https://mercadoinsight.cl/health/live` retorna HTTP 200 `{"status": "alive"}`.
  - `GET https://mercadoinsight.cl/health/ready` retorna HTTP 200 con todas las dependencias `healthy` (PostgreSQL, Redis, MinIO).
- [ ] **Autenticación**: Inicio de sesión exitoso en el frontend con obtención de token JWT.
- [ ] **Streaming SSE Asistente IA**: Petición de prueba a `/api/v1/chat/stream` emite tokens sin interrupciones.

---

## 6. Protocolo de Simulacros (Disaster Recovery Drills)

* **Frecuencia**: Se debe realizar un simulacro formal de recuperación **cada 3 meses**.
* **Procedimiento**:
  1. Seleccionar aleatoriamente un respaldo semanal o mensual del mes anterior.
  2. Restaurarlo en un entorno aislado (Recovery Sandbox).
  3. Ejecutar la suite de pruebas automatizadas contra el entorno recuperado:
     ```bash
     pytest apps/backend/tests -v -m "integration and not slow"
     ```
  4. Registrar fecha, tiempo total empleado (cronometrado vs RTO) y firma de los ingenieros participantes en la bitácora de continuidad operacional.

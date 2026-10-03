# Gestión de Migraciones de Base de Datos — MercadoInsight

Este documento detalla la arquitectura, directrices operacionales y procedimientos de despliegue y rollback para las migraciones de esquema en PostgreSQL utilizando **Alembic**, cumpliendo con la subfase **10.13 (Migraciones de base de datos)**.

---

## 1. Arquitectura de Migraciones con Alembic

Alembic gestiona la evolución incremental del esquema de base de datos de **MercadoInsight** (esquemas `public`, `staging`, `dw`, `knowledge`).

```text
       apps/backend/
       ├── alembic.ini              <- Configuración general y sys.path
       └── alembic/
           ├── env.py               <- Carga de Base.metadata y configuración dinámica de engine
           ├── script.py.mako       <- Plantilla para nuevas revisiones
           └── versions/            <- Historial inmutable y lineal de revisiones
               ├── 20260806_0001_create_adjudicacion_analytics_snapshots.py
               ├── ...
               └── 20260921_0018_create_ai_feedback_table.py (Head actual)
```

### Principios Fundamentales
1. **Historial Estrictamente Lineal**: No se permiten bifurcaciones ni múltiples cabezas (`heads`) en la rama `main`. Cada nueva migración debe declarar como `down_revision` la cabeza inmediatamente anterior.
2. **Idempotencia y Reversibilidad**: Toda migración debe implementar tanto la función `upgrade()` como la función `downgrade()` siempre que sea técnicamente viable.
3. **Control en Tabla de Metadatos**: Alembic persiste la versión aplicada actual en la tabla relacional `alembic_version (version_num VARCHAR(32) PRIMARY KEY)`.

---

## 2. Comandos Operativos Frecuentes

Los comandos se ejecutan desde el directorio `apps/backend` (o especificando `-c apps/backend/alembic.ini`):

```bash
# 1. Comprobar la cabeza (head) actual esperada en el código
alembic heads

# 2. Verificar la versión de esquema aplicada en la base de datos destino
alembic current

# 3. Comprobar si existen discrepancias entre los modelos SQLAlchemy y la BD
alembic check

# 4. Generar una nueva migración incremental autogenerada
alembic revision --autogenerate -m "add_column_x_to_table_y"

# 5. Aplicar todas las migraciones pendientes hasta la cabeza
alembic upgrade head

# 6. Revertir exactamente una revisión (Rollback)
alembic downgrade -1

# 7. Revertir hasta una revisión específica
alembic downgrade <revision_id>
```

---

## 3. Patrón Zero-Downtime: Expand / Contract

Para garantizar alta disponibilidad y evitar bloqueos exclusivos en tablas de gran volumen durante despliegues productivos, se aplica la estrategia **Expand / Contract**:

```text
Fase 1 (Expand)           Fase 2 (Deploy)          Fase 3 (Contract)
┌──────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ Agregar nueva columna│  │ Desplegar código que│  │ Migración posterior │
│ nullable o nuevo     │──│ escribe y lee ambas │──│ que elimina o limpia│
│ índice CONCURRENTLY  │  │ estructuras         │  │ la columna obsoleta │
└──────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### Reglas de Seguridad en PostgreSQL
* **Evitar bloqueos pesados en `ALTER TABLE`**: Nunca añadir una columna `NOT NULL` sin valor `DEFAULT` en tablas productivas con millones de registros. En PostgreSQL 11+, añadir columnas con `DEFAULT` constante es rápido, pero en tablas analíticas se recomienda crear primero la columna anulable (`nullable=True`), poblar los datos gradualmente y luego aplicar el constraint `NOT NULL`.
* **Creación de Índices Concurrente**: Para índices en tablas grandes (e.g. `licitaciones`, `licitacion_items`), utilizar `op.execute("CREATE INDEX CONCURRENTLY ...")` con `commit_as_you_go` para no bloquear lecturas ni escrituras concurrentes.
* **Extensiones PostgreSQL**: Extensiones requeridas como `uuid-ossp`, `pg_trgm` y `vector` (pgvector) deben ser inicializadas con `CREATE EXTENSION IF NOT EXISTS` en migraciones tempranas.

---

## 4. Integración en el Pipeline de Despliegue (CI/CD)

En [`deploy.yml`](file:///c:/Users/artut/market-insight/.github/workflows/deploy.yml), las migraciones se ejecutan de forma automatizada **antes** de iniciar el reemplazo progresivo de contenedores de la API:

1. **Paso 1**: Descarga de la nueva imagen o código verificado.
2. **Paso 2**: Ejecución del comando de migración:
   ```bash
   docker compose --env-file .env.prod run --rm backend alembic upgrade head
   ```
3. **Paso 3**: Si la migración falla, el pipeline aborta de inmediato impidiendo el despliegue de los nuevos contenedores.
4. **Paso 4**: Si la migración triunfa, se reinician los contenedores `backend` y `worker` con rolling restart.

---

## 5. Procedimiento de Rollback de Migraciones

Si una migración causa fallos imprevistos tras el despliegue:

1. **Detener el tráfico incidente**: NGINX redirige temporalmente las peticiones si es crítico.
2. **Identificar la revisión defectuosa**:
   ```bash
   alembic current
   ```
3. **Ejecutar el rollback**:
   ```bash
   alembic downgrade -1
   ```
4. **Validar consistencia de datos**:
   Verificar que las claves foráneas, índices y secuencias se encuentren en estado consistente.
5. **Verificar estado de salud**:
   Comprobar que los endpoints de liveness y readiness responden con HTTP 200:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

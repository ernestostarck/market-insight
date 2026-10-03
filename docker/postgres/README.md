# PostgreSQL 17

Esta carpeta contiene la base PostgreSQL de MercadoInsight para desarrollo local.

## Capas

- `conf/`: configuración del servidor y acceso.
- `init/`: scripts de bootstrap para extensiones, roles, schemas, tipos, funciones, triggers, índices y seed.

## Validación local

```bash
docker compose up -d postgres
```

Dentro del contenedor o desde `psql`:

```sql
SELECT version();
SELECT extname FROM pg_extension ORDER BY extname;
SELECT rolname FROM pg_roles ORDER BY rolname;
SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;
```

## Notas

- Se mantiene PostgreSQL 17.
- `documents.document_metadata` es la tabla base para archivos y metadatos.
- `procurement.tenders` es la tabla base inicial para licitaciones.
# Database

## Objetivo

Diseñar una base de datos orientada a analitica, trazabilidad y busqueda semantica, no solo a transacciones simples.

## Motor

- PostgreSQL como base principal.
- pgvector para embeddings.
- PostGIS para consultas geograficas y territorio.

## Fase 1.3

La base de datos arranca con una imagen compatible con PostGIS y pgvector, extensiones habilitadas y bootstrap de roles y esquema:

- `uuid-ossp`
- `pg_trgm`
- `vector`
- `postgis`
- `market_insight_admin`
- `market_insight_app`
- Esquema `market_insight`

## Zonas de datos

### Operational Data Store

- Licitaciones crudas.
- Ofertas.
- Adjudicaciones.
- Ordenes de compra.
- Proveedores.
- Organismos compradores.

### Analytical Warehouse

- Hechos de licitacion.
- Hechos de oferta.
- Historicos de precios.
- Historial de scoring.
- Snapshots de mercado.

### Semantic Layer

- Embeddings de documentos.
- Embeddings de licitaciones.
- Clasificaciones NLP.
- Resultados de similitud.

## Estrategia de migraciones

- Alembic como gestor de versiones.
- Migraciones incrementales por fase.
- Seeds solo para datos de soporte y catálogos.

## Reglas de modelado

- Entidades claras y normalizadas.
- Campos de auditoria en tablas criticas.
- Separacion entre payload crudo y modelo normalizado.
- Indices para busqueda por codigo, fecha, estado, categoria y proveedor.

## Proxima etapa

La siguiente version documentara el modelo relacional base y el esquema de hechos/dimensiones para analitica.

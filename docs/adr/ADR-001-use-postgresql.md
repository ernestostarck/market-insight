# ADR-001: Uso de PostgreSQL 17 como Motor Principal de Base de Datos

- **Status**: Aceptado
- **Fecha**: 2026-08-15
- **Decisores**: Equipo de Arquitectura MercadoInsight

---

## Contexto
MercadoInsight requiere almacenar y procesar millones de compras públicas, órdenes de compra y oferentes de ChileCompra. Los datos presentan una combinación de estructuras altamente normalizadas (proveedores, organismos, adjudicaciones) junto con atributos semiestructurados no homogéneos (especificaciones técnicas y bases en JSONB). Se evaluó si convenía una base de datos relacional tradicional, una base de datos NoSQL documental o un motor híbrido.

## Decisión
Adoptar **PostgreSQL 17** como motor primario de base de datos relacional, documental y analítico para toda la plataforma.

## Alternativas Consideradas
1. **MongoDB**: Fuerte soporte para documentos JSONB, pero carece de integridad referencial ACID estricta y transacciones complejas entre ofertas y adjudicaciones.
2. **MySQL / MariaDB**: Buen soporte relacional, pero soporte inferior para tipos JSONB indexados (`GIN`), extensiones avanzadas y búsqueda de texto completo en español.
3. **CockroachDB**: Excelente escalabilidad horizontal, pero complejidad operacional innecesaria para la etapa actual y compatibilidad parcial con ciertas extensiones nativas.

## Consecuencias
- **Positivas**:
  - Soporte nativo y de alto rendimiento para columnas `JSONB` indexadas con `GIN`.
  - Integridad referencial ACID garantizada en los esquemas `core` y `dw`.
  - Ecosistema maduro de extensiones (`pgvector`, `pg_trgm`, `unaccent`, `postgis`).
  - Soporte para migraciones declarativas y lineales mediante SQLAlchemy y Alembic.
- **Negativas**:
  - Requiere dimensionamiento cuidadoso de memoria compartida (`shared_buffers`, `work_mem`) y monitoreo de conexiones concurrentes vía pool.

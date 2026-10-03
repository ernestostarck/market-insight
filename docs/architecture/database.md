# Arquitectura de Base de Datos — PostgreSQL & pgvector

Este documento detalla el diseño de almacenamiento de **MercadoInsight**, implementado en **PostgreSQL 17** con extensiones avanzadas para soporte vectorial, geoespacial y búsqueda de texto completo.

---

## 1. Esquemas Lógicos

La base de datos está organizada en esquemas independientes para garantizar desacoplamiento y permisos de acceso según roles:

```text
PostgreSQL 17
├── public      # Extensiones y tablas administrativas
├── core        # Datos canónicos normalizados de ChileCompra
├── analytics   # Snapshots operacionales, agregaciones y KPIs
├── knowledge   # Conocimiento semántico derivado, embeddings y taxonomía
├── dw          # Tablas de hechos y dimensiones históricas
└── marts       # Vistas materializadas y agregados para el dashboard
```

| Esquema | Propósito | Principales Tablas / Vistas |
| :--- | :--- | :--- |
| `core` | Almacenamiento normalizado de compras públicas | `organismos`, `proveedores`, `licitaciones`, `items`, `ofertas`, `adjudicaciones`, `ordenes_compra` |
| `analytics` | Métricas de scoring, oportunidades y snapshots | `adjudicacion_snapshots`, `market_opportunity_scores`, `risk_indicators` |
| `knowledge` | Capa semántica de IA y NLP | `taxonomies`, `rule_classifications`, `embeddings`, `ner_entities`, `ai_conversations`, `ai_messages`, `ai_feedback` |
| `dw` | Data warehouse dimensional | `dim_tiempo`, `dim_organismo`, `dim_proveedor`, `dim_rubro`, `fact_adjudicaciones` |
| `marts` | Vistas de alto rendimiento para frontend | `mart_monthly_spending`, `mart_supplier_concentration`, `mart_geriatric_demand` |

---

## 2. Extensiones de PostgreSQL

1. **`vector` (`pgvector`)**:
   - Soporte para vectores densos de punto flotante (`vector(384)` para `all-MiniLM-L6-v2` o `vector(1536)` para OpenAI text-embedding-3-small).
   - Índices **HNSW** (`Hierarchical Navigable Small World`) con métrica de distancia coseno (`vector_cosine_ops`) para consultas con latencia menor a 15ms sobre millones de registros.
2. **`pg_trgm`**:
   - Búsqueda trigramática para tolerancia a errores tipográficos y búsqueda difusa (*fuzzy search*) en nombres de licitaciones y proveedores.
3. **`unaccent`**:
   - Eliminación automática de tildes en búsquedas textuales en español.
4. **`uuid-ossp`**:
   - Generación de identificadores universales únicos v4.

---

## 3. Estrategia de Indexación

- **Claves Primarias y Únicas**: UUIDs generados por el servidor o códigos de licitación oficiales indexados con B-Tree.
- **Búsqueda de Texto Completo (FTS)**:
  ```sql
  CREATE INDEX idx_licitaciones_fts ON core.licitaciones 
  USING gin(to_tsvector('spanish', coalesce(nombre, '') || ' ' || coalesce(descripcion, '')));
  ```
- **Índice Vectorial HNSW**:
  ```sql
  CREATE INDEX idx_embeddings_hnsw ON knowledge.embeddings 
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
  ```
- **Índices Parciales y Compuestos**: Optimización para filtros frecuentes (por ejemplo, licitaciones activas por región y fecha de cierre).

---

## 4. Migraciones con Alembic

- **Linealidad Estricta**: Una única rama principal con un solo head (`single-head`) verificada en CI/CD.
- **Patrón Zero-Downtime**: Estrategia *Expand / Contract*:
  1. Adición de nuevas columnas como anulables (`nullable=True`).
  2. Creación de índices con `CREATE INDEX CONCURRENTLY` para no bloquear lecturas ni escrituras.
  3. Despliegue de código que escribe en ambas versiones.
  4. Migración de datos y posterior eliminación de campos obsoletos.
- **Rollback Garantizado**: Cada script de migración implementa rigurosamente tanto `upgrade()` como `downgrade()`.
